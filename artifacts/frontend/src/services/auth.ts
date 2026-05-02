import { api } from "@/services/api";
import axios from "axios";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
}

export async function login(credentials: LoginCredentials): Promise<string> {
  const params = new URLSearchParams();
  params.append("username", credentials.email);
  params.append("password", credentials.password);

  const response = await axios.post("/api/auth/token", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  const token = response.data.access_token;
  localStorage.setItem("auth_token", token);
  return token;
}

export async function register(data: RegisterData): Promise<void> {
  await api.post("/auth/register", data);
}

export async function logout(): Promise<void> {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("active_store_id");
  window.location.href = "/login";
}

export function getToken(): string | null {
  return localStorage.getItem("auth_token");
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export async function getCurrentUser(): Promise<any> {
  const response = await api.get("/auth/me");
  return response.data;
}
