import { configureStore, createAsyncThunk, createSlice } from '@reduxjs/toolkit'

const API = 'http://localhost:8000'

export const loadHcps = createAsyncThunk('crm/loadHcps', async () => {
  const r = await fetch(`${API}/api/hcps`)
  return r.json()
})

export const loadInteractions = createAsyncThunk('crm/loadInteractions', async () => {
  const r = await fetch(`${API}/api/interactions`)
  return r.json()
})

export const sendAgentMessage = createAsyncThunk('crm/sendAgentMessage', async ({message, currentForm}) => {
  const r = await fetch(`${API}/api/agent/chat`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message, current_form: currentForm})
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || 'Agent request failed')
  return data
})

export const logStructuredInteraction = createAsyncThunk('crm/logStructured', async (payload) => {
  const r = await fetch(`${API}/api/interactions`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || 'Could not log interaction')
  return data
})

const crm = createSlice({
  name: 'crm',
  initialState: {
    hcps: [], interactions: [], loading: false,
    messages: [{role: 'assistant', text: 'Log interaction details here (e.g., "Met Dr. Smith, discussed Prodo-X efficacy, positive sentiment, shared brochure") or ask for help.'}],
    lastTool: null, lastExtracted: null, toast: ''
  },
  reducers: { clearToast: s => {s.toast = ''}, localUser: (s,a) => {s.messages.push({role:'user', text:a.payload})} },
  extraReducers: b => b
    .addCase(loadHcps.fulfilled, (s,a) => {s.hcps = a.payload})
    .addCase(loadInteractions.fulfilled, (s,a) => {s.interactions = a.payload})
    .addCase(sendAgentMessage.pending, s => {s.loading = true})
    .addCase(sendAgentMessage.fulfilled, (s,a) => {
      s.loading = false
      s.messages.push({role:'assistant', text:a.payload.response})
      s.lastTool = a.payload.tool_used
      s.lastExtracted = a.payload.extracted
    })
    .addCase(sendAgentMessage.rejected, (s,a) => {
      s.loading = false; s.messages.push({role:'assistant', text:`Error: ${a.error.message}`})
    })
    .addCase(logStructuredInteraction.fulfilled, (s,a) => {s.toast = a.payload.message})
})

export const {clearToast} = crm.actions
export const store = configureStore({reducer: {crm: crm.reducer}})
