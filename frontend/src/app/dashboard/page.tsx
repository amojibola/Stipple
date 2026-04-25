"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError, Project, QuotaResponse, UserProfile } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  processing: "bg-yellow-100 text-yellow-700",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${cls}`}>
      {status}
    </span>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

interface DeleteDialogProps {
  projectName: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}

function DeleteDialog({ projectName, onConfirm, onCancel, isDeleting }: DeleteDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
        <h3 className="text-base font-semibold text-gray-900">Delete project?</h3>
        <p className="mt-2 text-sm text-gray-600">
          <span className="font-medium">{projectName}</span> and its source image will be
          permanently deleted. This cannot be undone.
        </p>
        <div className="mt-5 flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
          >
            {isDeleting && (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            )}
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

interface ProjectCardProps {
  project: Project;
  onDelete: (project: Project) => void;
}

function ProjectCard({ project, onDelete }: ProjectCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-3 hover:border-indigo-300 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-medium text-gray-900 truncate">{project.name}</h3>
          <p className="text-xs text-gray-400 mt-0.5">{formatDate(project.created_at)}</p>
        </div>
        <StatusBadge status={project.status} />
      </div>
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onDelete(project)}
          className="text-xs text-red-600 hover:text-red-800 font-medium"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [user, setUser] = useState<UserProfile | null>(null);
  const [quota, setQuota] = useState<QuotaResponse | null>(null);
  const [quotaError, setQuotaError] = useState(false);

  const [confirmDelete, setConfirmDelete] = useState<Project | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const loadProjects = useCallback(async (p: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.projects.list(p, 20);
      setProjects(data.items);
      setTotal(data.total);
      setPage(data.page);
      setPages(data.pages);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects(1);
    api.users.me().then(setUser).catch(() => null);
    api.users.quota().then(setQuota).catch(() => setQuotaError(true));
  }, [loadProjects]);

  const handleDeleteConfirm = useCallback(async () => {
    if (!confirmDelete) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.projects.delete(confirmDelete.id);
      setConfirmDelete(null);
      // Reload current page; if it's now empty and not page 1, go back one page
      const nextPage = projects.length === 1 && page > 1 ? page - 1 : page;
      loadProjects(nextPage);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setIsDeleting(false);
    }
  }, [confirmDelete, page, projects.length, loadProjects]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">My Projects</h1>
        <div className="flex items-center gap-4">
          {user && (
            <span className="text-sm text-gray-500">{user.email}</span>
          )}
          <Link
            href="/editor"
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            New project
          </Link>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Quota bar */}
        {quotaError && (
          <div className="mb-6 bg-white rounded-xl border border-gray-200 px-5 py-4 text-sm text-gray-400">
            Quota information unavailable
          </div>
        )}
        {!quotaError && quota && (
          <div className="mb-6 bg-white rounded-xl border border-gray-200 px-5 py-4 flex flex-wrap gap-6 text-sm text-gray-600">
            <span>
              Daily renders:{" "}
              <strong className="text-gray-900">
                {quota.renders_today} / {quota.daily_limit}
              </strong>
            </span>
            <span>
              Monthly renders:{" "}
              <strong className="text-gray-900">
                {quota.renders_this_month} / {quota.monthly_limit}
              </strong>
            </span>
          </div>
        )}

        {/* Project list */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-24">
            <p className="text-sm text-red-500">{error}</p>
            <button
              onClick={() => loadProjects(page)}
              className="mt-3 text-sm text-indigo-600 hover:underline"
            >
              Retry
            </button>
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-24">
            <p className="text-sm text-gray-400">No projects yet.</p>
            <Link
              href="/editor"
              className="mt-3 inline-block text-sm text-indigo-600 hover:underline"
            >
              Create your first project
            </Link>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map((p) => (
                <ProjectCard
                  key={p.id}
                  project={p}
                  onDelete={setConfirmDelete}
                />
              ))}
            </div>

            {/* Pagination */}
            {pages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-3">
                <button
                  onClick={() => { setPage(page - 1); loadProjects(page - 1); }}
                  disabled={page <= 1}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-500">
                  Page {page} of {pages} — {total} project{total !== 1 ? "s" : ""}
                </span>
                <button
                  onClick={() => { setPage(page + 1); loadProjects(page + 1); }}
                  disabled={page >= pages}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            )}

            {pages <= 1 && total > 0 && (
              <p className="mt-6 text-center text-sm text-gray-400">
                {total} project{total !== 1 ? "s" : ""}
              </p>
            )}
          </>
        )}
      </main>

      {/* Delete confirmation dialog */}
      {confirmDelete && (
        <DeleteDialog
          projectName={confirmDelete.name}
          onConfirm={handleDeleteConfirm}
          onCancel={() => { setConfirmDelete(null); setDeleteError(null); }}
          isDeleting={isDeleting}
        />
      )}

      {/* Delete error toast */}
      {deleteError && (
        <div className="fixed bottom-4 right-4 bg-red-600 text-white text-sm px-4 py-3 rounded-lg shadow-lg">
          {deleteError}
        </div>
      )}
    </div>
  );
}
