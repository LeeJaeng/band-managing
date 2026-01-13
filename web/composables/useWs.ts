import { onUnmounted, ref } from "vue";

export type WsUser = {
  id: string;
  name: string;
  part?: string | null;
};

export function useWs(sessionId: string, user: WsUser) {
  const events = ref<any[]>([]);
  const connected = ref(false);
  const lastMessageAt = ref<number | null>(null);

  if (!sessionId || !user?.id || !user?.name) {
    return { events, connected, lastMessageAt };
  }

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${protocol}://${location.host}/ws`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    connected.value = true;
    ws.send(
      JSON.stringify({
        type: "JOIN_SESSION",
        session_id: sessionId,
        user: {
          id: user.id,
          name: user.name,
          part: user.part ?? null,
        },
      })
    );
  };

  ws.onmessage = (e) => {
    lastMessageAt.value = Date.now();
    try {
      const msg = JSON.parse(e.data);
      events.value = [msg, ...events.value].slice(0, 50);
    } catch {}
  };

  ws.onerror = () => {
    connected.value = false;
  };

  ws.onclose = () => {
    connected.value = false;
  };

  onUnmounted(() => {
    try {
      ws.close();
    } catch {}
  });

  return { events, connected, lastMessageAt };
}