import React, { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Bot, CalendarDays, CheckCircle2, Clock3, Search, Send, Sparkles, Stethoscope, Mic, MicOff } from 'lucide-react'
import { loadHcps, loadInteractions, logStructuredInteraction, sendAgentMessage } from './store'

const nowLocal = () => {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0,16)
}

function App() {
  const dispatch = useDispatch()
  const {hcps, interactions, messages, loading, lastTool, toast, lastExtracted} = useSelector(s => s.crm)
  const [chat, setChat] = useState('')
  const [form, setForm] = useState({
    hcp_name: '', interaction_type: 'Meeting', interaction_date: nowLocal(),
    attendees: '', topics: '', materials_shared: '', samples_distributed: '',
    sentiment: 'Neutral', outcomes: '', follow_up_required: false
  })

  // Voice recording states
  const [isRecording, setIsRecording] = useState(false)
  const [mediaRecorder, setMediaRecorder] = useState(null)
  const [voiceStatus, setVoiceStatus] = useState('')

  // Load HCPs and Interactions on mount
  useEffect(() => {
    dispatch(loadHcps())
    dispatch(loadInteractions())
  }, [dispatch])

  // Reactive reload of HCPs and Interactions lists when updates occur
  useEffect(() => {
    dispatch(loadHcps())
    dispatch(loadInteractions())
  }, [dispatch, toast, lastTool])

  // Populate left form when AI agent extracts fields
  useEffect(() => {
    if (lastExtracted && lastExtracted.tool === 'log_interaction') {
      if (lastExtracted.is_commit) {
        // Successfully logged/committed! Reset the form draft
        setForm({
          hcp_name: '', interaction_type: 'Meeting', interaction_date: nowLocal(),
          attendees: '', topics: '', materials_shared: '', samples_distributed: '',
          sentiment: 'Neutral', outcomes: '', follow_up_required: false
        })
      } else {
        // It's a draft update. Populate/update the draft fields!
        setForm({
          hcp_name: lastExtracted.hcp_name || '',
          interaction_type: lastExtracted.interaction_type || 'Meeting',
          interaction_date: lastExtracted.interaction_date ? new Date(lastExtracted.interaction_date).toISOString().slice(0,16) : nowLocal(),
          attendees: lastExtracted.attendees || '',
          topics: lastExtracted.topics || '',
          materials_shared: lastExtracted.materials_shared || '',
          samples_distributed: lastExtracted.samples_distributed || '',
          sentiment: lastExtracted.sentiment || 'Neutral',
          outcomes: lastExtracted.outcomes || '',
          follow_up_required: lastExtracted.follow_up_required || false
        })
      }
    }
  }, [lastExtracted])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      const chunks = []

      recorder.ondataavailable = e => {
        if (e.data.size > 0) {
          chunks.push(e.data)
        }
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop())
        const blob = new Blob(chunks, { type: 'audio/webm' })
        if (blob.size === 0) return

        setVoiceStatus('Processing voice note...')
        try {
          const formData = new FormData()
          formData.append('file', blob, 'voicenote.webm')

          const response = await fetch('http://localhost:8000/api/transcribe-summary', {
            method: 'POST',
            body: formData,
          })

          if (!response.ok) {
            throw new Error('Failed to transcribe and summarize audio')
          }

          const data = await response.json()
          if (data.summary) {
            // Populate Topics Discussed, and try to split or set outcomes if appropriate
            setForm(prev => ({
              ...prev,
              topics: prev.topics ? `${prev.topics}\n\n${data.summary}` : data.summary
            }))
            setVoiceStatus('Voice note summarized successfully!')
          } else {
            setVoiceStatus('Could not transcribe audio. Speak clearly.')
          }
        } catch (err) {
          console.error(err)
          setVoiceStatus('Error transcribing audio. Check backend connection.')
        } finally {
          setTimeout(() => setVoiceStatus(''), 4000)
        }
      }

      recorder.start()
      setMediaRecorder(recorder)
      setIsRecording(true)
      setVoiceStatus('Recording voice note... Click again to stop.')
    } catch (err) {
      console.error(err)
      setVoiceStatus('Microphone access denied or not supported.')
      setTimeout(() => setVoiceStatus(''), 4000)
    }
  }

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
      setIsRecording(false)
    }
  }

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const update = e => setForm({...form, [e.target.name]: e.target.type === 'checkbox' ? e.target.checked : e.target.value})

  const submitForm = e => {
    e.preventDefault()
    dispatch(logStructuredInteraction({...form, interaction_date: new Date(form.interaction_date).toISOString()}))
  }
  
  const submitChat = e => {
    e.preventDefault()
    if (!chat.trim() || loading) return
    const text = chat.trim()
    setChat('')
    dispatch({type:'crm/localUser', payload:text})
    dispatch(sendAgentMessage({message: text, currentForm: form}))
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand"><span className="brandMark"><Stethoscope size={19}/></span><span>HCPulse</span><b>AI CRM</b></div>
        <div className="rep"><span className="online"></span> Field Representative Workspace</div>
      </header>

      <section className="workspace">
        <div className="formPane">
          <div className="titleRow">
            <div><p className="eyebrow">HCP MODULE</p><h1>Log HCP Interaction</h1><p className="sub">Capture field engagement in a structured CRM record.</p></div>
            <span className="aiBadge"><Sparkles size={14}/> AI-first workflow</span>
          </div>

          {toast && <div className="toast"><CheckCircle2 size={18}/>{toast}</div>}

          <form onSubmit={submitForm}>
            <h3>Interaction Details</h3>
            <div className="grid2">
              <label>HCP Name
                <div className="fieldIcon"><Search size={17}/><input
                  required
                  name="hcp_name"
                  value={form.hcp_name}
                  onChange={update}
                  list="hcp-list"
                  placeholder="Search or enter HCP name..."
                  style={{ paddingLeft: '38px' }}
                />
                <datalist id="hcp-list">
                  {Array.isArray(hcps) && hcps.map(h => <option key={h.id} value={h.name}>{h.name} — {h.specialty}</option>)}
                </datalist></div>
              </label>
              <label>Interaction Type
                <select name="interaction_type" value={form.interaction_type} onChange={update}>
                  <option>Meeting</option><option>Call</option><option>Virtual Meeting</option><option>Conference</option>
                </select>
              </label>
              <label>Date & Time
                <div className="fieldIcon"><CalendarDays size={17}/><input name="interaction_date" type="datetime-local" value={form.interaction_date} onChange={update}/></div>
              </label>
              <label>Attendees<input name="attendees" value={form.attendees} onChange={update} placeholder="Enter names or team members..."/></label>
            </div>

            <label style={{ marginBottom: '8px' }}>Topics Discussed
              <textarea required name="topics" value={form.topics} onChange={update} placeholder="Enter key discussion points, product interest, objections or outcomes..." style={{ minHeight: '120px' }}/>
            </label>

            {/* Summarize from Voice Note link exactly matching screenshot */}
            <div style={{ marginBottom: '22px' }}>
              <button
                type="button"
                onClick={toggleRecording}
                className={`voice-note-btn ${isRecording ? 'recording' : ''}`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'transparent',
                  border: 'none',
                  color: isRecording ? '#d32f2f' : '#3b82f6',
                  padding: 0,
                  fontSize: '13px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  outline: 'none',
                  textDecoration: 'none'
                }}
              >
                <span>🎙️</span>
                <span>{isRecording ? 'Stop Recording' : 'Summarize from Voice Note (Requires Consent)'}</span>
              </button>
              {voiceStatus && (
                <small style={{
                  display: 'block',
                  marginTop: '4px',
                  color: voiceStatus.includes('Error') || voiceStatus.includes('denied') ? '#d32f2f' : '#059669',
                  fontWeight: '600',
                  fontSize: '11px'
                }}>
                  {voiceStatus}
                </small>
              )}
            </div>

            {/* Materials Shared with Search/Add button */}
            <div style={{ marginBottom: '22px' }}>
              <strong style={{ fontSize: '13px', color: '#465167', display: 'block', marginBottom: '8px' }}>Materials Shared</strong>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <input
                  name="materials_shared"
                  value={form.materials_shared}
                  onChange={update}
                  placeholder="e.g. Brochures, Clinical trial papers"
                  style={{ margin: 0 }}
                />
                <button
                  type="button"
                  onClick={() => alert('Search/Add materials')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    whiteSpace: 'nowrap',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    fontSize: '12px',
                    fontWeight: '600',
                    background: '#fff',
                    color: '#4b5563',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  🔍 Search/Add
                </button>
              </div>
            </div>

            {/* Samples Distributed with Add Sample button */}
            <div style={{ marginBottom: '22px' }}>
              <strong style={{ fontSize: '13px', color: '#465167', display: 'block', marginBottom: '8px' }}>Samples Distributed</strong>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <input
                  name="samples_distributed"
                  value={form.samples_distributed}
                  onChange={update}
                  placeholder="e.g. CardioPlus 10mg samples"
                  style={{ margin: 0 }}
                />
                <button
                  type="button"
                  onClick={() => alert('Add sample')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    whiteSpace: 'nowrap',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    fontSize: '12px',
                    fontWeight: '600',
                    background: '#fff',
                    color: '#4b5563',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  ➕ Add Sample
                </button>
              </div>
            </div>

            {/* Observed Sentiment Radios with custom styling and emojis */}
            <div style={{ marginBottom: '22px' }}>
              <strong style={{ fontSize: '13px', color: '#465167', display: 'block', marginBottom: '8px' }}>Observed/Inferred HCP Sentiment</strong>
              <div style={{ display: 'flex', gap: '24px', padding: '4px 0' }}>
                <label className="sentiment-radio-label">
                  <input
                    type="radio"
                    name="sentiment"
                    value="Positive"
                    checked={form.sentiment === 'Positive'}
                    onChange={update}
                  />
                  <span>😃 Positive</span>
                </label>
                <label className="sentiment-radio-label">
                  <input
                    type="radio"
                    name="sentiment"
                    value="Neutral"
                    checked={form.sentiment === 'Neutral'}
                    onChange={update}
                  />
                  <span>😐 Neutral</span>
                </label>
                <label className="sentiment-radio-label">
                  <input
                    type="radio"
                    name="sentiment"
                    value="Negative"
                    checked={form.sentiment === 'Negative'}
                    onChange={update}
                  />
                  <span>😡 Negative</span>
                </label>
              </div>
            </div>

            {/* Outcomes text area */}
            <label style={{ marginBottom: '22px' }}>Outcomes
              <textarea
                name="outcomes"
                value={form.outcomes}
                onChange={update}
                placeholder="Key outcomes or agreements..."
                style={{ minHeight: '80px' }}
              />
            </label>

            <div className="grid2 lower" style={{ marginTop: '10px' }}>
              <label className="checkCard" style={{ height: '48px', margin: 0 }}>
                <input type="checkbox" name="follow_up_required" checked={form.follow_up_required} onChange={update}/>
                <span><b>Follow-up required</b><small>Mark this interaction for a future action.</small></span>
              </label>
            </div>
            
            <button className="primary" type="submit" style={{ marginTop: '20px' }}>Log Interaction</button>
          </form>

          {/* Recent Logged Interactions list view */}
          <div className="recent-list-section" style={{ marginTop: '45px', borderTop: '1px solid #edf0f5', paddingTop: '30px', clear: 'both' }}>
            <h2 style={{ fontSize: '20px', marginBottom: '15px', fontWeight: '700', letterSpacing: '-0.4px' }}>Recent Logged Interactions</h2>
            {!Array.isArray(interactions) || interactions.length === 0 ? (
              <p style={{ color: '#8a94a6', fontSize: '13px' }}>No interactions logged yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '15px' }}>
                {Array.isArray(interactions) && interactions.map(item => (
                  <div key={item.id} className="interaction-card" style={{
                    border: '1px solid #e6eaf1',
                    borderRadius: '12px',
                    padding: '16px',
                    background: '#fafbfc',
                    fontSize: '13px',
                    lineHeight: '1.6',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.01)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <strong style={{ fontSize: '14px', color: '#1677e8', fontWeight: '700' }}>{item.hcp_name}</strong>
                      <span style={{
                        background: item.sentiment === 'Positive' ? '#ecfbf4' : item.sentiment === 'Neutral' ? '#f3f4f6' : '#fff1f1',
                        color: item.sentiment === 'Positive' ? '#16754c' : item.sentiment === 'Neutral' ? '#4b5563' : '#b91c1c',
                        padding: '4px 10px',
                        borderRadius: '16px',
                        fontSize: '11px',
                        fontWeight: '600'
                      }}>{item.sentiment}</span>
                    </div>
                    <div style={{ color: '#465167', marginBottom: '8px', fontSize: '12px' }}>
                      <span style={{ fontWeight: '600' }}>{item.interaction_type}</span> &middot; {new Date(item.interaction_date).toLocaleString()}
                    </div>
                    <p style={{ margin: '0 0 8px', color: '#657188', whiteSpace: 'pre-wrap' }}>{item.topics}</p>
                    {item.outcomes && <p style={{ margin: '0 0 8px', color: '#465167', fontSize: '12px' }}>🎯 <b>Outcomes:</b> {item.outcomes}</p>}
                    {item.samples_distributed && <p style={{ margin: '0 0 8px', color: '#465167', fontSize: '12px' }}>🎁 <b>Samples:</b> {item.samples_distributed}</p>}
                    {item.materials_shared && <p style={{ margin: '0 0 8px', color: '#465167', fontSize: '12px' }}>📄 <b>Materials:</b> {item.materials_shared}</p>}
                    {item.follow_up_required && (
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#fef3c7', color: '#92400e', padding: '3px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: '700' }}>
                        ⚠️ Follow-up Required
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <aside className="chatPane">
          <div className="chatHeader">
            <div className="botIcon"><Bot/></div>
            <div>
              <h2>🤖 AI Assistant</h2>
              <p>Log Interaction details here via chat</p>
            </div>
          </div>
          <div className="agentStatus"><span></span>{lastTool ? `Last tool: ${lastTool.replaceAll('_',' ')}` : 'Agent ready · 5 CRM tools connected'}</div>
          
          <div className="messages">
            {Array.isArray(messages) && messages.map((m,i) => {
              // Custom class naming based on messages content
              let styleClass = 'assistant';
              if (m.role === 'user') {
                styleClass = 'user';
              } else if (m.text.includes('logged successfully') || m.text.includes('success')) {
                styleClass = 'assistant-success';
              }
              return (
                <div key={i} className={`message ${styleClass}`}>
                  {m.text}
                </div>
              );
            })}
            {loading && <div className="message assistant typing">Analyzing intent and selecting a tool…</div>}
          </div>
          
          <form className="chatInput" onSubmit={submitChat}>
            <textarea value={chat} onChange={e=>setChat(e.target.value)} placeholder='Describe Interaction...'/>
            <button disabled={loading} className="ai-send-btn">
              <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', fontSize: '10px', gap: '2px' }}>
                <Sparkles size={16}/>
                <span>Log</span>
              </span>
            </button>
          </form>
          <p className="hint"><Clock3 size={13}/> Natural language → LLM extraction → LangGraph routing → CRM tool</p>
        </aside>
      </section>
    </main>
  )
}

export default App
