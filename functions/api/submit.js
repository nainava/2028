export async function onRequestPost(context) {
  const { request, env } = context;

  let data;
  try {
    data = await request.json();
  } catch {
    return Response.json({ error: "invalid JSON" }, { status: 400 });
  }

  const name = (data.name || "").trim().slice(0, 32) || "Anon";
  const tiers = data.tiers || {};

  if (typeof tiers !== "object" || Array.isArray(tiers)) {
    return Response.json({ error: "tiers must be an object" }, { status: 400 });
  }

  // Generate 6-char alphanumeric ID
  const alphabet = "abcdefghijklmnopqrstuvwxyz0123456789";
  let sid;
  for (let attempt = 0; attempt < 10; attempt++) {
    const bytes = new Uint8Array(6);
    crypto.getRandomValues(bytes);
    sid = Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
    const existing = await env.SUBMISSIONS.get(sid);
    if (!existing) break;
    if (attempt === 9) {
      return Response.json({ error: "could not generate unique id" }, { status: 500 });
    }
  }

  await env.SUBMISSIONS.put(
    sid,
    JSON.stringify({
      id: sid,
      name,
      tiers,
      created_at: new Date().toISOString(),
    })
  );

  const url = new URL("/" + sid, request.url).href;
  return Response.json({ id: sid, url });
}
