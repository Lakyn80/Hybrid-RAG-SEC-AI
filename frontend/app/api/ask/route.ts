import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") || "http://rag-api:8021";
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const runId = request.headers.get("x-run-id")?.trim();
    const upstream = await fetch(`${getBackendBaseUrl()}/api/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(runId ? { "X-Run-ID": runId } : {}),
      },
      body,
      cache: "no-store",
    });

    const payload = await upstream.text();

    return new Response(payload, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
        ...(upstream.headers.get("x-run-id")
          ? { "X-Run-ID": String(upstream.headers.get("x-run-id")) }
          : {}),
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Frontend proxy failed to reach the backend.";

    return Response.json(
      {
        error: message,
      },
      { status: 502 },
    );
  }
}
