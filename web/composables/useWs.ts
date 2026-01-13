// web/composables/useWs.ts
import { ref, onUnmounted } from 'vue'

export function useWs(sessionId: string) {
  const events = ref<any[]>([])
  const connected = ref(false)
  const lastMessageAt = ref<number | null>(null)

  if (!sessionId) {
    return { events, connected, lastMessageAt }
  }

  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${protocol}://${location.host}/ws`)

  ws.onopen = () => {
    connected.value = true
    ws.send(JSON.stringify({
      type: 'JOIN_SESSION',
      session_id: sessionId
    }))
  }

  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      events.value.unshift(data)
      lastMessageAt.value = Date.now()
    } catch {}
  }

  ws.onclose = () => {
    connected.value = false
  }

  onUnmounted(() => {
    ws.close()
  })

  return { events, connected, lastMessageAt }
}