export async function onRequestGet(context) {
  const { params, env } = context;
  const sid = params.id;

  const data = await env.SUBMISSIONS.get(sid, { type: "json" });
  if (!data) {
    return Response.json({ error: "not found" }, { status: 404 });
  }

  return Response.json(data);
}
