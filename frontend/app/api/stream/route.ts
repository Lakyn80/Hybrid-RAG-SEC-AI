import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") || "http://rag-api:8021";
}

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("query")?.trim();

  if (!query) {
    return Response.json({ error: "Missing query parameter." }, { status: 400 });
  }

  try {
    const upstream = await fetch(
      `${getBackendBaseUrl()}/api/stream?${new URLSearchParams({ query }).toString()}`,
      {
        method: "GET",
        headers: {
          Accept: "text/event-stream",
          "Cache-Control": "no-cache",
        },
        cache: "no-store",
      },
    );

    if (!upstream.ok || !upstream.body) {
      const payload = await upstream.text();
      return new Response(payload || "Upstream stream failed.", {
        status: upstream.status || 502,
        headers: {
          "Content-Type": upstream.headers.get("content-type") || "text/plain; charset=utf-8",
          "Cache-Control": "no-cache",
        },
      });
    }

    return new Response(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Frontend stream proxy failed to reach the backend.";

    return new Response(`data: error\n\ndata: ${message}\n\n`, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  }
}
