"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, StippleParams, UploadedFile } from "@/lib/api";

const DEFAULT_PARAMS: StippleParams = {
  dot_size: 2.5,
  density: 0.7,
  black_point: 15,
  highlights: 0.25,
  shadow_depth: 0.6,
};

type UploadState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "done"; file: UploadedFile }
  | { status: "error"; message: string };

type PreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; url: string }
  | { status: "error"; message: string };

type JobState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "polling"; jobId: string; jobStatus: string }
  | { status: "complete"; jobId: string }
  | { status: "failed"; message: string }
  | { status: "expired" };

interface SliderProps {
  label: string;
  name: keyof StippleParams;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (name: keyof StippleParams, value: number) => void;
}

function Slider({ label, name, min, max, step, value, onChange }: SliderProps) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-700 font-medium">{label}</span>
        <span className="text-gray-500 tabular-nums">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(name, parseFloat(e.target.value))}
        className="w-full accent-indigo-600"
      />
    </div>
  );
}

export default function EditorPage() {
  const [uploadState, setUploadState] = useState<UploadState>({ status: "idle" });
  const [isDragging, setIsDragging] = useState(false);
  const [params, setParams] = useState<StippleParams>(DEFAULT_PARAMS);
  const [previewState, setPreviewState] = useState<PreviewState>({ status: "idle" });
  const [jobState, setJobState] = useState<JobState>({ status: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);
  const previewUrlRef = useRef<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const jobIdRef = useRef<string | null>(null);

  const fetchPreview = useCallback(async (fileId: string, p: StippleParams) => {
    setPreviewState({ status: "loading" });
    try {
      const blob = await api.images.preview(fileId, p);
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
      const url = URL.createObjectURL(blob);
      previewUrlRef.current = url;
      setPreviewState({ status: "done", url });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Preview failed";
      setPreviewState({ status: "error", message });
    }
  }, []);

  // Debounced preview on param or file change
  useEffect(() => {
    if (uploadState.status !== "done") return;
    const fileId = uploadState.file.id;

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchPreview(fileId, params);
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [params, uploadState, fetchPreview]);

  // Job status polling
  useEffect(() => {
    if (jobState.status !== "polling") {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    const id = jobState.jobId;
    jobIdRef.current = id;

    pollRef.current = setInterval(async () => {
      try {
        const data = await api.jobs.getStatus(id);
        if (data.status === "complete") {
          setJobState({ status: "complete", jobId: id });
        } else if (data.status === "failed") {
          setJobState({
            status: "failed",
            message: data.error_message || "Render failed",
          });
        } else if (data.status === "expired") {
          setJobState({ status: "expired" });
        } else {
          setJobState((prev) =>
            prev.status === "polling"
              ? { ...prev, jobStatus: data.status }
              : prev
          );
        }
      } catch {
        // polling errors are transient — keep polling
      }
    }, 5000);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobState.status]);

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  const handleParamChange = useCallback(
    (name: keyof StippleParams, value: number) => {
      setParams((prev) => ({ ...prev, [name]: value }));
      setJobState({ status: "idle" });
    },
    []
  );

  const handleFile = useCallback(async (file: File) => {
    setUploadState({ status: "uploading" });
    setPreviewState({ status: "idle" });
    setJobState({ status: "idle" });
    try {
      const result = await api.images.upload(file);
      setUploadState({ status: "done", file: result });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Upload failed. Please try again.";
      setUploadState({ status: "error", message });
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleSubmitRender = useCallback(async () => {
    if (uploadState.status !== "done") return;
    setJobState({ status: "submitting" });
    try {
      const { job_id } = await api.jobs.create(uploadState.file.id, params);
      setJobState({ status: "polling", jobId: job_id, jobStatus: "queued" });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Render submission failed";
      setJobState({ status: "failed", message });
    }
  }, [uploadState, params]);

  const handleDownload = useCallback(async () => {
    if (jobState.status !== "complete") return;
    try {
      await api.jobs.downloadResult(jobState.jobId);
    } catch {
      // download errors don't need to change job state
    }
  }, [jobState]);

  const reset = () => {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = null;
    setUploadState({ status: "idle" });
    setPreviewState({ status: "idle" });
    setJobState({ status: "idle" });
    setParams(DEFAULT_PARAMS);
    if (inputRef.current) inputRef.current.value = "";
  };

  const isEditing = uploadState.status === "done";

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Stipple Editor</h1>
        {isEditing && (
          <button onClick={reset} className="text-sm text-indigo-600 hover:underline">
            Upload new image
          </button>
        )}
      </header>

      <main className="flex-1 flex p-6 gap-6">
        {!isEditing ? (
          <div className="flex-1 flex items-center justify-center">
            {uploadState.status === "uploading" ? (
              <div className="flex flex-col items-center gap-4">
                <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm text-gray-600">Uploading...</p>
              </div>
            ) : (
              <div className="w-full max-w-lg space-y-4">
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => inputRef.current?.click()}
                  onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  className={`
                    w-full h-64 border-2 border-dashed rounded-xl flex flex-col items-center
                    justify-center gap-3 cursor-pointer transition-colors select-none
                    ${isDragging
                      ? "border-indigo-500 bg-indigo-50"
                      : "border-gray-300 bg-white hover:border-indigo-400 hover:bg-indigo-50"
                    }
                  `}
                >
                  <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 48 48" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" />
                  </svg>
                  <div className="text-center">
                    <p className="text-sm font-medium text-gray-700">
                      Drop an image here, or{" "}
                      <span className="text-indigo-600">browse</span>
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      JPEG, PNG, or WebP — up to 10 MB, max 4000px per side
                    </p>
                  </div>
                </div>
                <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleChange} />
                {uploadState.status === "error" && (
                  <p className="text-sm text-red-600 text-center">{uploadState.message}</p>
                )}
              </div>
            )}
          </div>
        ) : (
          <>
            {/* Left: controls */}
            <div className="w-72 shrink-0 flex flex-col gap-5">
              <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-5">
                <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">Parameters</h2>
                <Slider label="Dot Size" name="dot_size" min={0.5} max={10} step={0.5} value={params.dot_size} onChange={handleParamChange} />
                <Slider label="Density" name="density" min={0.1} max={1.0} step={0.05} value={params.density} onChange={handleParamChange} />
                <Slider label="Black Point" name="black_point" min={0} max={100} step={1} value={params.black_point} onChange={handleParamChange} />
                <Slider label="Highlights" name="highlights" min={0.0} max={1.0} step={0.05} value={params.highlights} onChange={handleParamChange} />
                <Slider label="Shadow Depth" name="shadow_depth" min={0.0} max={1.0} step={0.05} value={params.shadow_depth} onChange={handleParamChange} />
              </div>

              {/* Export controls */}
              <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
                <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">Export</h2>
                <p className="text-xs text-gray-500">
                  Full-resolution render — uses daily quota.
                </p>

                {jobState.status === "idle" || jobState.status === "failed" ? (
                  <>
                    <button
                      onClick={handleSubmitRender}
                      className="w-full py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      Start Render
                    </button>
                    {jobState.status === "failed" && (
                      <p className="text-xs text-red-600">{jobState.message}</p>
                    )}
                  </>
                ) : jobState.status === "submitting" ? (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    Submitting...
                  </div>
                ) : jobState.status === "polling" ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                      <span className="capitalize">{jobState.jobStatus}...</span>
                    </div>
                    <p className="text-xs text-gray-400">Checking every 5 seconds</p>
                  </div>
                ) : jobState.status === "complete" ? (
                  <button
                    onClick={handleDownload}
                    className="w-full py-2 px-4 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    Download PNG
                  </button>
                ) : jobState.status === "expired" ? (
                  <p className="text-xs text-gray-500">
                    This render output has expired and is no longer available.
                    Start a new render to generate a fresh copy.
                  </p>
                ) : null}
              </div>

              <div className="text-xs text-gray-400 px-1">
                {uploadState.file.width_px} × {uploadState.file.height_px}px
                &nbsp;&middot;&nbsp;{uploadState.file.megapixels} MP
                &nbsp;&middot;&nbsp;{(uploadState.file.file_size_bytes / 1024).toFixed(0)} KB
              </div>
            </div>

            {/* Right: preview */}
            <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden flex items-center justify-center min-h-96">
              {previewState.status === "idle" && (
                <p className="text-sm text-gray-400">Adjust parameters to generate preview</p>
              )}
              {previewState.status === "loading" && (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-sm text-gray-400">Generating preview...</p>
                </div>
              )}
              {previewState.status === "done" && (
                <img
                  src={previewState.url}
                  alt="Stipple preview"
                  className="max-w-full max-h-full object-contain"
                />
              )}
              {previewState.status === "error" && (
                <p className="text-sm text-red-500">{previewState.message}</p>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
