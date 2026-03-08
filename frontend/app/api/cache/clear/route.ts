export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") || "http://rag-api:8021";
}

export async function POST() {
  try {
    const upstream = await fetch(`${getBackendBaseUrl()}/api/cache/clear`, {
      method: "POST",
      cache: "no-store",
    });

    const payload = await upstream.text();

    return new Response(payload, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Frontend proxy failed to clear the backend cache.";

    return Response.json(
      {
        error: message,
      },
      { status: 502 },
    );
  }
}
