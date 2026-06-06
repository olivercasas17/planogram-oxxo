import axios from "axios";
import type { JobResult, OptimizeRequest, OptimizeResponse, UploadResponse } from "../types/api";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export const uploadCsv = (file: File): Promise<UploadResponse> => {
  const form = new FormData();
  form.append("file", file);
  return api
    .post<UploadResponse>("/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const startOptimize = (payload: OptimizeRequest): Promise<OptimizeResponse> =>
  api.post<OptimizeResponse>("/optimize", payload).then((r) => r.data);

export const getJobResult = (jobId: string): Promise<JobResult> =>
  api.get<JobResult>(`/optimize/result/${jobId}`).then((r) => r.data);

export default api;
