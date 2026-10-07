/**
 * API client for the backend.
 * Supports: (1) photo + optional report, (2) text/chat + follow-up answers. At least one path required.
 */

const API_BASE = '/api'

/**
 * @param {File|null} skinFile - optional skin image
 * @param {File|null} bloodReportFile - optional blood report
 * @param {Object} textPayload - optional: { text_input, skin_type_self, concerns, uses_actives, sensitivities }
 */
export async function analyzeSkin(skinFile, bloodReportFile = null, textPayload = null) {
  const form = new FormData()

  if (skinFile) {
    form.append('skin_image', skinFile)
  }
  if (bloodReportFile) {
    form.append('blood_report', bloodReportFile)
  }

  if (textPayload) {
    if (textPayload.text_input) form.append('text_input', textPayload.text_input)
    if (textPayload.skin_type_self) form.append('skin_type_self', textPayload.skin_type_self)
    if (textPayload.concerns) form.append('concerns', textPayload.concerns)
    if (textPayload.uses_actives) form.append('uses_actives', textPayload.uses_actives)
    if (textPayload.sensitivities) form.append('sensitivities', textPayload.sensitivities)
  }

  let res
  try {
    res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      body: form,
    })
  } catch {
    throw new Error(
      'Cannot reach the analysis server. Start the app with npm start so the backend runs on port 8000.'
    )
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const msg = Array.isArray(err.detail) ? err.detail.map((e) => e.msg || e).join(', ') : (err.detail || 'Analysis failed')
    throw new Error(msg)
  }

  return res.json()
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error('API unhealthy')
  return res.json()
}

/**
 * Post-report feedback: appreciation or ingredient that doesn't suit / not available.
 * @param {string} message - User message
 * @param {object} [routineSummary] - Optional summary of current routine for context
 */
export async function sendFeedback(message, routineSummary = null) {
  let res
  try {
    res = await fetch(`${API_BASE}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, routine_summary: routineSummary }),
    })
  } catch {
    throw new Error('Cannot reach the server. Make sure the backend is running.')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to send feedback')
  }
  return res.json()
}
