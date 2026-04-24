"use client";

import { useCallback, useRef, useState } from "react";
import { api, ApiError, UploadedFile } from "@/lib/api";

type UploadState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "done"; file: UploadedFile }
  | { status: "error"; message: string };

export default function EditorPage() {
  const [uploadState, setUploadState] = useState<UploadState>({ status: "idle" });
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    setUploadState({ status: "uploading" });
    try {
      const result = await api.images.upload(file);
      setUploadState({ status: "done", file: result });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Upload failed. Please try again.";
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

  const reset = () => {
    setUploadState({ status: "idle" });
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Stipple Editor</h1>
      </header>

      <main className="flex-1 flex items-center justify-center p-6">
        {uploadState.status === "idle" || uploadState.status === "error" ? (
          <div className="w-full max-w-lg space-y-4">
            <div
              role="button"
              tabIndex={0}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
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
              <svg
                className="w-12 h-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 48 48"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                />
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

            <input
              ref={inputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleChange}
            />

            {uploadState.status === "error" && (
              <p className="text-sm text-red-600 text-center">
                {uploadState.message}
              </p>
            )}
          </div>
        ) : uploadState.status === "uploading" ? (
          <div className="flex flex-col items-center gap-4">
            <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-600">Uploading...</p>
          </div>
        ) : (
          <div className="w-full max-w-2xl space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <img
                src={api.images.getUrl(uploadState.file.id)}
                alt="Uploaded image"
                className="w-full object-contain max-h-96"
              />
            </div>
            <div className="flex items-center justify-between text-sm text-gray-500 px-1">
              <span>
                {uploadState.file.width_px} × {uploadState.file.height_px}px
                &nbsp;&middot;&nbsp;
                {uploadState.file.megapixels} MP
                &nbsp;&middot;&nbsp;
                {(uploadState.file.file_size_bytes / 1024).toFixed(0)} KB
              </span>
              <button
                onClick={reset}
                className="text-indigo-600 hover:underline text-sm"
              >
                Upload a different image
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
