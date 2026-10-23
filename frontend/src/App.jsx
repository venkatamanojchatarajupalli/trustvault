
import { useEffect, useState } from 'react'
import './App.css'


const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'


function getErrorMessage(data, fallback) {
  if (Array.isArray(data?.detail)) {
    return data.detail.map(item => item.msg).join(', ')
  }

  if (data?.detail) return String(data.detail)
  if (data?.message) return String(data.message)

  return fallback
}

function formatDate(value) {
  if (!value) return 'Date unavailable'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return String(value)

  return date.toLocaleString()
}

function getDocumentName(document) {
  return (
    document.title ||
    document.filename ||
    document.file_name ||
    document.name ||
    `Document ${document.id ?? ''}`.trim()
  )
}

function getAuditDescription(event) {
  return (
    event.action ||
    event.event_type ||
    event.event ||
    event.description ||
    event.action_type ||
    'Security event'
  )
}

function App() {
  const [authMode, setAuthMode] = useState('')
  const [notice, setNotice] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const [isSignedIn, setIsSignedIn] = useState(
    Boolean(sessionStorage.getItem('trustvault_token'))
  )
  const [documents, setDocuments] = useState([])
  const [auditEvents, setAuditEvents] = useState([])
  const [incidents, setIncidents] = useState([])
  const [incidentsLoading, setIncidentsLoading] = useState(false)
  const [incidentsError, setIncidentsError] = useState('')
  const [incidentDocumentId, setIncidentDocumentId] = useState('')
  const [incidentDescription, setIncidentDescription] = useState('')
  const [incidentSubmitting, setIncidentSubmitting] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)
  const [dataLoading, setDataLoading] = useState(false)
  const [activeSection, setActiveSection] = useState('Dashboard')
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadFile, setUploadFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [shareEmails, setShareEmails] = useState({})
  const [shareEditAccess, setShareEditAccess] = useState({})
  const [permissionsByDocument, setPermissionsByDocument] = useState({})
  const [permissionsVisible, setPermissionsVisible] = useState({})
  const [sharingDocumentId, setSharingDocumentId] = useState(null)
  const [permissionsLoadingId, setPermissionsLoadingId] = useState(null)
  const [revokingPermissionId, setRevokingPermissionId] = useState(null)
  const sharedDocuments = documents.filter(
    document =>
      currentUser &&
      Number(document.owner_id) !== Number(currentUser.id)
  )
  async function apiRequest(path, options = {}) {
    const token = sessionStorage.getItem('trustvault_token')

    const headers = {
      ...(options.headers || {}),
    }

    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    })

    const contentType = response.headers.get('content-type') || ''
    let data = null

    if (contentType.includes('application/json')) {
      data = await response.json()
    } else if (!options.download) {
      data = await response.text()
    }

    if (response.status === 401) {
      sessionStorage.removeItem('trustvault_token')
      setIsSignedIn(false)
      setDocuments([])
      setAuditEvents([])
      setCurrentUser(null)
      setNotice('Your session has expired. Please sign in again.')
    }

    if (!response.ok) {
      throw new Error(
        typeof data === 'object' && data !== null
          ? getErrorMessage(data, `Request failed (${response.status}).`)
          : `Request failed (${response.status}).`
      )
    }

    return { response, data }
  }

  async function loadDashboardData() {
    const token = sessionStorage.getItem('trustvault_token')

    if (!token) {
      setIsSignedIn(false)
      setDocuments([])
      setAuditEvents([])
      setCurrentUser(null)
      return
    }

    setDataLoading(true)

    const results = await Promise.allSettled([
      apiRequest('/api/auth/me'),
      apiRequest('/api/documents'),
      apiRequest('/api/audit/my-events'),
    ])

    const userResult = results[0]
    const documentResult = results[1]
    const auditResult = results[2]

    if (userResult.status === 'fulfilled') {
      setCurrentUser(userResult.value.data)
    } else {
      setCurrentUser(null)
      setNotice(`Could not load account role: ${userResult.reason.message}`)
    }

    if (documentResult.status === 'fulfilled') {
      const data = documentResult.value.data

      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.documents)
          ? data.documents
          : Array.isArray(data?.items)
            ? data.items
            : []

      setDocuments(list)
    } else {
      setNotice(
        `Could not load documents: ${documentResult.reason.message}`
      )
    }

    if (auditResult.status === 'fulfilled') {
      const data = auditResult.value.data

      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.events)
          ? data.events
          : Array.isArray(data?.items)
            ? data.items
            : []

      setAuditEvents(list)
    } else if (auditResult.reason?.message) {
      setNotice(current =>
        current
          ? `${current} Audit activity: ${auditResult.reason.message}`
          : `Could not load audit activity: ${auditResult.reason.message}`
      )
    }

    setDataLoading(false)
  }
  async function loadIncidents() {
  setIncidentsLoading(true)
  setIncidentsError('')

  try {
    const { data } = await apiRequest('/api/admin/incidents')

    const list = Array.isArray(data)
      ? data
      : Array.isArray(data?.items)
        ? data.items
        : []

    setIncidents(list)
  } catch (error) {
    setIncidents([])
    setIncidentsError(error.message || 'Could not load incidents.')
  } finally {
    setIncidentsLoading(false)
  }
}
async function handleCreateIncident(event) {
  event.preventDefault()
  setIncidentsError('')

  const documentId = Number(incidentDocumentId)

  if (!Number.isInteger(documentId) || documentId <= 0) {
    setIncidentsError('Enter a valid positive document ID.')
    return
  }

  if (incidentDescription.trim().length < 5) {
    setIncidentsError('Description must contain at least 5 characters.')
    return
  }

  setIncidentSubmitting(true)

  try {
    await apiRequest('/api/admin/incidents', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        document_id: documentId,
        description: incidentDescription.trim(),
      }),
    })

    setIncidentDocumentId('')
    setIncidentDescription('')
    await loadIncidents()
    setNotice('Incident reported successfully.')
  } catch (error) {
    setIncidentsError(error.message || 'Could not report the incident.')
  } finally {
    setIncidentSubmitting(false)
  }
}
useEffect(() => {
  if (activeSection === 'Incidents' && isSignedIn) {
    loadIncidents()
  }
}, [activeSection, isSignedIn])

  useEffect(() => {
    if (isSignedIn) {
      loadDashboardData()
    }
  }, [isSignedIn])

  async function handleAuth(event) {
    event.preventDefault()
    setNotice('')
    setIsLoading(true)

    const formData = new FormData(event.currentTarget)
    const mode = authMode

    const payload = {
      email: formData.get('email'),
      password: formData.get('password'),
    }

    if (mode === 'register') {
      payload.name = formData.get('name')
    }

    try {
      const endpoint =
        mode === 'login'
          ? '/api/auth/login'
          : '/api/auth/register'

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        setNotice(
          getErrorMessage(data, `Request failed (${response.status}).`)
        )
        return
      }

      if (mode === 'login') {
        if (!data.access_token) {
          setNotice('Login response did not contain an access token.')
          return
        }

        sessionStorage.setItem('trustvault_token', data.access_token)
        setIsSignedIn(true)
        setAuthMode('')
        setNotice('Login successful. You are securely signed in.')
        setActiveSection('Dashboard')
      } else {
        setAuthMode('login')
        setNotice('Account created successfully. Please sign in.')
      }
    } catch {
      setNotice(
        'Could not connect to the backend. Check that the backend is running and CORS is configured.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  function signOut() {
    sessionStorage.removeItem('trustvault_token')
    setIsSignedIn(false)
    setDocuments([])
    setAuditEvents([])
    setCurrentUser(null)
    setAuthMode('')
    setActiveSection('Dashboard')
    setNotice('You have signed out.')
  }


  async function handleUpload(event) {
    event.preventDefault()

    if (!uploadFile) {
      setNotice('Please choose a file to upload.')
      return
    }

    setNotice('')
    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('title', uploadTitle.trim() || uploadFile.name)
      formData.append('file', uploadFile)

      await apiRequest('/api/documents/upload', {
        method: 'POST',
        body: formData,
      })

      setNotice('Document uploaded successfully.')
      setUploadTitle('')
      setUploadFile(null)

      const fileInput = window.document.getElementById('document-file-input')
      if (fileInput) fileInput.value = ''

      await loadDashboardData()
    } catch (error) {
      setNotice(`Upload failed: ${error.message}`)
    } finally {
      setUploading(false)
    }
  }

  async function handleDownload(doc) {
  try {
    const response = await fetch(
      `${API_URL}/api/documents/${doc.id}/download`,
      {
        headers: {
          Authorization: `Bearer ${sessionStorage.getItem('trustvault_token')}`,
        },
      }
    )

    if (!response.ok) {
      const message = await response.text()
      throw new Error(message || `Download failed (${response.status})`)
    }

    const blob = await response.blob()
    const objectUrl = window.URL.createObjectURL(blob)
    const link = window.document.createElement('a')

    link.href = objectUrl
    link.download = doc.filename || doc.file_name || doc.title || `document-${doc.id}`
    window.document.body.appendChild(link)
    link.click()
    link.remove()

    window.setTimeout(() => {
      window.URL.revokeObjectURL(objectUrl)
    }, 1000)

    setNotice('Document downloaded successfully.')
  } catch (error) {
    setNotice(`Download failed: ${error.message}`)
  }
}

  async function handleShare(doc) {
    const email = (shareEmails[doc.id] || '').trim()

    if (!email) {
      setNotice('Enter the recipient email address before sharing.')
      return
    }

    setSharingDocumentId(doc.id)
    setNotice('')

    try {
      await apiRequest(`/api/documents/${doc.id}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          can_edit: Boolean(shareEditAccess[doc.id]),
        }),
      })

      setNotice(`Document shared with ${email}.`)
      setShareEmails(current => ({ ...current, [doc.id]: '' }))
      await loadPermissions(doc, true)
    } catch (error) {
      setNotice(`Sharing failed: ${error.message}`)
    } finally {
      setSharingDocumentId(null)
    }
  }

  async function loadPermissions(doc, keepVisible = false) {
    setPermissionsLoadingId(doc.id)

    try {
      const { data } = await apiRequest(`/api/documents/${doc.id}/permissions`)
      const permissions = Array.isArray(data)
        ? data
        : Array.isArray(data?.permissions)
          ? data.permissions
          : Array.isArray(data?.items)
            ? data.items
            : []

      setPermissionsByDocument(current => ({ ...current, [doc.id]: permissions }))
      setPermissionsVisible(current => ({ ...current, [doc.id]: keepVisible || !current[doc.id] }))
    } catch (error) {
      setNotice(`Could not load permissions: ${error.message}`)
    } finally {
      setPermissionsLoadingId(null)
    }
  }

  async function handleRevokePermission(doc, permission) {
    if (!window.confirm(`Revoke access for user ID ${permission.user_id}?`)) return

    setRevokingPermissionId(permission.id)
    setNotice('')

    try {
      await apiRequest(
        `/api/documents/${doc.id}/share/${permission.id}`,
        { method: 'DELETE' }
      )
      setNotice(`Access revoked for user ID ${permission.user_id}.`)
      const { data } = await apiRequest(`/api/documents/${doc.id}/permissions`)
      const permissions = Array.isArray(data)
        ? data
        : Array.isArray(data?.permissions)
          ? data.permissions
          : Array.isArray(data?.items)
            ? data.items
            : []
      setPermissionsByDocument(current => ({ ...current, [doc.id]: permissions }))
      setPermissionsVisible(current => ({ ...current, [doc.id]: true }))
    } catch (error) {
      setNotice(`Could not revoke access: ${error.message}`)
    } finally {
      setRevokingPermissionId(null)
    }
  }

  function selectSection(section) {
    setActiveSection(section)
    setNotice('')
  }

  const recentDocuments = [...documents].slice(0, 5)
  const recentEvents = [...auditEvents].slice(0, 5)

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h2 className="brand">◈ TrustVault</h2>
        <p className="sidebar-label">WORKSPACE</p>

        <nav>
          {[
            'Dashboard',
            'Documents',
            'Shared with me',
            'Audit trail',
            'Incidents',
          ].map((item, index) => (
            <button
              className={`nav-item ${activeSection === item ? 'active' : ''}`}
              key={item}
              onClick={() => selectSection(item)}
            >
              <span>{['▦', '▤', '⇄', '◷', '⚑'][index]}</span>
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="secure-icon">✓</div>
          <strong>Your files, protected.</strong>
          <p>Private storage. Controlled access. Auditable actions.</p>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">Workspace</span>
            <span className="crumb-divider"> / </span>
            {activeSection}
          </div>

          <div className="top-actions">
            <span className="security-pill">
              <span className="green-dot" /> System secure
            </span>

            {isSignedIn ? (
              <button className="button button-outline" onClick={signOut}>
                Sign out
              </button>
            ) : (
              <>
                <button
                  className="button button-outline"
                  onClick={() => {
                    setNotice('')
                    setAuthMode('login')
                  }}
                >
                  Sign in
                </button>
                <button
                  className="button button-primary"
                  onClick={() => {
                    setNotice('')
                    setAuthMode('register')
                  }}
                >
                  Create account ↗
                </button>
              </>
            )}
          </div>
        </header>

        {activeSection === 'Dashboard' && (
          <>
            {isSignedIn && currentUser && (
              <section className="panel" style={{ marginBottom: '18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                <div>
                  <strong>Signed in as {currentUser.name || currentUser.email || 'User'}</strong>
                  <p style={{ margin: '4px 0 0', color: 'var(--muted, #64748b)' }}>Account role</p>
                </div>
                <span style={{ display: 'inline-flex', alignItems: 'center', padding: '7px 12px', borderRadius: '999px', fontWeight: 700, fontSize: '13px', background: String(currentUser.role).toLowerCase() === 'admin' || String(currentUser.role).toLowerCase() === 'administrator' ? '#dcfce7' : '#e0f2fe', color: String(currentUser.role).toLowerCase() === 'admin' || String(currentUser.role).toLowerCase() === 'administrator' ? '#166534' : '#075985' }}>
                  {String(currentUser.role || 'unknown').toLowerCase() === 'admin' ? 'Administrator' : String(currentUser.role || 'Unknown role').replace(/^\w/, character => character.toUpperCase())}
                </span>
              </section>
            )}
            <section className="hero">
              <div className="hero-copy">
                <span className="eyebrow">
                  <span className="green-dot" /> YOUR SECURE WORKSPACE
                </span>
                <h1>
                  Every document.<br />
                  Under your <span>control.</span>
                </h1>
                <p>
                  A secure home for your important files. Manage access, track
                  activity, and keep sensitive documents protected.
                </p>
                <div className="hero-actions">
                  <button
                    className="button button-primary"
                    onClick={() =>
                      isSignedIn
                        ? selectSection('Documents')
                        : setAuthMode('register')
                    }
                  >
                    {isSignedIn ? 'View documents' : 'Get started'} <span>→</span>
                  </button>
                  <button
                    className="button button-outline"
                    onClick={() =>
                      setNotice(
                        'TrustVault checks permissions and records security-relevant activity.'
                      )
                    }
                  >
                    Explore security ↗
                  </button>
                </div>
              </div>

              <div className="hero-art">
                <div className="orbit orbit-one" />
                <div className="orbit orbit-two" />
                <div className="document-illustration">
                  <div className="doc-lock">◇</div>
                  <div className="doc-line long" />
                  <div className="doc-line medium" />
                  <div className="doc-line short" />
                  <div className="doc-footer">
                    <span>TV</span>
                    <span className="mini-check">✓</span>
                  </div>
                </div>
                <div className="floating-card card-verified">
                  <span className="float-icon">✓</span>
                  <div>
                    <strong>Access verified</strong>
                    <small>Permission checked</small>
                  </div>
                </div>
                <div className="floating-card card-private">
                  <span className="float-icon">◈</span>
                  <div>
                    <strong>Private by design</strong>
                    <small>Your files stay protected</small>
                  </div>
                </div>
              </div>
            </section>

            <div className="section-heading">
              <div>
                <span className="eyebrow">OVERVIEW</span>
                <h2>Your workspace at a glance</h2>
              </div>
              <span className="muted">
                {dataLoading ? 'Loading live data…' : isSignedIn ? 'Live data' : 'Sign in to load data'}
              </span>
            </div>

            <section className="stats-grid">
              <article className="stat-card">
                <div className="stat-top">
                  <span>▤</span>
                  <span className="stat-tag">Workspace</span>
                </div>
                <h3>Documents</h3>
                <strong>{isSignedIn ? documents.length : '—'}</strong>
                <p>{isSignedIn ? 'Documents accessible to you' : 'Sign in to view your files'}</p>
              </article>

              <article className="stat-card">
                <div className="stat-top">
                  <span>⇄</span>
                  <span className="stat-tag">Permissions</span>
                </div>
                <h3>Shared with me</h3>
                <strong>—</strong>
                <p>Shared-access count not yet connected</p>
              </article>

              <article className="stat-card">
                <div className="stat-top">
                  <span>◷</span>
                  <span className="stat-tag">Monitoring</span>
                </div>
                <h3>Audit events</h3>
                <strong>{isSignedIn ? auditEvents.length : '—'}</strong>
                <p>{isSignedIn ? 'Events returned by the audit API' : 'Sign in to view activity'}</p>
              </article>

              <article className="stat-card">
                <div className="stat-top">
                  <span>✓</span>
                  <span className="stat-tag">Protection</span>
                </div>
                <h3>Security status</h3>
                <strong className="status-text">Protected</strong>
                <p>Backend access controls enabled</p>
              </article>
            </section>

            <section className="lower-grid">
              <article className="panel">
                <div className="panel-heading">
                  <div>
                    <h3>Recent documents</h3>
                    <p>Your latest files in one place</p>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => selectSection('Documents')}
                  >
                    View all →
                  </button>
                </div>

                {isSignedIn && recentDocuments.length > 0 ? (
                  <div className="live-list">
                    {recentDocuments.map((document, index) => (
                      <div className="activity-row" key={document.id ?? index}>
                        <span className="activity-icon">▤</span>
                        <div>
                          <strong>{getDocumentName(document)}</strong>
                          <p>{formatDate(document.created_at || document.uploaded_at)}</p>
                        </div>
                        {document.id != null && (
                          <button
                            className="text-button"
                            onClick={() => handleDownload(document)}
                          >
                            Download
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <div className="empty-icon">▤</div>
                    <strong>
                      {isSignedIn ? 'No documents returned' : 'Your documents will appear here'}
                    </strong>
                    <p>
                      {isSignedIn
                        ? 'Upload a document to get started.'
                        : 'Sign in to securely access your files and permissions.'}
                    </p>
                    <button
                      className="button button-outline"
                      onClick={() =>
                        isSignedIn
                          ? selectSection('Documents')
                          : setAuthMode('login')
                      }
                    >
                      {isSignedIn ? 'Manage documents' : 'Sign in to continue'}
                    </button>
                  </div>
                )}
              </article>

              <article className="panel activity-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Security activity</h3>
                    <p>Recent events from the audit API</p>
                  </div>
                  <span className="live-label">
                    <span className="green-dot" /> {isSignedIn ? 'CONNECTED' : 'SIGNED OUT'}
                  </span>
                </div>

                {isSignedIn && recentEvents.length > 0 ? (
                  recentEvents.map((event, index) => (
                    <div className="activity-row" key={event.id ?? index}>
                      <span className="activity-icon">◷</span>
                      <div>
                        <strong>{getAuditDescription(event)}</strong>
                        <p>
                          {formatDate(
                            event.created_at || event.timestamp || event.occurred_at
                          )}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <>
                    <div className="activity-row">
                      <span className="activity-icon">✓</span>
                      <div>
                        <strong>Permission checks</strong>
                        <p>Protected actions are checked by the backend.</p>
                      </div>
                    </div>
                    <div className="activity-row">
                      <span className="activity-icon">◷</span>
                      <div>
                        <strong>Audit trail</strong>
                        <p>
                          {isSignedIn
                            ? 'No audit events were returned.'
                            : 'Sign in to load your audit activity.'}
                        </p>
                      </div>
                    </div>
                    <div className="activity-row">
                      <span className="activity-icon">◇</span>
                      <div>
                        <strong>Private file storage</strong>
                        <p>Files are handled by the backend service.</p>
                      </div>
                    </div>
                  </>
                )}
              </article>
            </section>
          </>
        )}

        {activeSection === 'Documents' && (
          <section className="content-section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">YOUR FILES</span>
                <h2>Documents</h2>
              </div>
              <button
                className="button button-outline"
                onClick={loadDashboardData}
                disabled={dataLoading}
              >
                {dataLoading ? 'Refreshing…' : 'Refresh'}
              </button>
            </div>

            {isSignedIn ? (
              <>
                <article className="panel upload-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Upload a document</h3>
                      <p>Choose a file and send it to secure backend storage.</p>
                    </div>
                  </div>

                  <form className="auth-form" onSubmit={handleUpload}>
                    <label>
                      Document title
                      <input
                        value={uploadTitle}
                        onChange={event => setUploadTitle(event.target.value)}
                        placeholder="Enter a document title"
                        maxLength={200}
                      />
                    </label>

                    <label>
                      Choose file
                      <input
                        id="document-file-input"
                        type="file"
                        required
                        onChange={event =>
                          setUploadFile(event.target.files?.[0] || null)
                        }
                      />
                    </label>

                    <button
                      className="button button-primary submit-button"
                      type="submit"
                      disabled={uploading}
                    >
                      {uploading ? 'Uploading…' : 'Upload document →'}
                    </button>
                  </form>
                </article>

                <article className="panel documents-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Your documents</h3>
                      <p>{documents.length} document(s) returned by the API</p>
                    </div>
                  </div>

                  {dataLoading ? (
                    <p>Loading documents…</p>
                  ) : documents.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-icon">▤</div>
                      <strong>No documents found</strong>
                      <p>Upload a document using the form above.</p>
                    </div>
                  ) : (
                    <div className="live-list">
                      {documents.map((document, index) => (
                        <div className="activity-row" key={document.id ?? index}>
                          <span className="activity-icon">▤</span>
                          <div className="document-share-content">
                            <strong>{getDocumentName(document)}</strong>
                            {currentUser && Number(document.owner_id) === Number(currentUser.id) && (
                              <span style={{ display: 'inline-flex', marginLeft: '8px', padding: '3px 8px', borderRadius: '999px', background: '#ede9fe', color: '#5b21b6', fontSize: '11px', fontWeight: 700, verticalAlign: 'middle' }}>Owner</span>
                            )}
                            <p>
                              ID: {document.id ?? 'Unavailable'} ·{' '}
                              {formatDate(document.created_at || document.uploaded_at)}
                            </p>
                            {document.id != null && (
  <>
    {currentUser &&
      Number(document.owner_id) === Number(currentUser.id) && (
        <div className="document-share-tools">
                                <form
                                  className="share-form"
                                  onSubmit={event => {
                                    event.preventDefault()
                                    handleShare(document)
                                  }}
                                >
                                  <label>
                                    Share with email
                                    <input
                                      type="email"
                                      value={shareEmails[document.id] || ''}
                                      onChange={event =>
                                        setShareEmails(current => ({
                                          ...current,
                                          [document.id]: event.target.value,
                                        }))
                                      }
                                      placeholder="recipient@example.com"
                                      required
                                    />
                                  </label>
                                  <label className="share-edit-option">
                                    <input
                                      type="checkbox"
                                      checked={Boolean(shareEditAccess[document.id])}
                                      onChange={event =>
                                        setShareEditAccess(current => ({
                                          ...current,
                                          [document.id]: event.target.checked,
                                        }))
                                      }
                                    />
                                    Allow editing
                                  </label>
                                  <button
                                    className="button button-primary"
                                    type="submit"
                                    disabled={sharingDocumentId === document.id}
                                  >
                                    {sharingDocumentId === document.id ? 'Sharing…' : 'Share'}
                                  </button>
                                </form>
                                <button
                                  className="button button-outline"
                                  type="button"
                                  onClick={() => {
                                    if (permissionsVisible[document.id]) {
                                      setPermissionsVisible(current => ({
                                        ...current,
                                        [document.id]: false,
                                      }))
                                    } else {
                                      loadPermissions(document)
                                    }
                                  }}
                                  disabled={permissionsLoadingId === document.id}
                                >
                                  {permissionsLoadingId === document.id
                                    ? 'Loading access…'
                                    : permissionsVisible[document.id]
                                      ? 'Hide access'
                                      : 'Manage access'}
                                </button>
                                {permissionsVisible[document.id] && (
                                  <div className="permission-list">
                                    <strong>Document permissions</strong>
                                    {(permissionsByDocument[document.id] || []).length === 0 ? (
                                      <p>No permission records returned.</p>
                                    ) : (
                                      (permissionsByDocument[document.id] || []).map(permission => {
                                        const isRevoked = Boolean(permission.revoked_at)
                                        return (
                                          <div className="permission-item" key={permission.id}>
                                            <div>
                                              <strong>User ID {permission.user_id}</strong>
                                              <p>
                                                {permission.can_edit ? 'Read and edit' : 'Read only'}
                                                {' · '}{isRevoked ? 'Revoked' : 'Active'}
                                              </p>
                                            </div>
                                            {!isRevoked && (
                                              <button
                                                className="button button-outline"
                                                type="button"
                                                onClick={() => handleRevokePermission(document, permission)}
                                                disabled={revokingPermissionId === permission.id}
                                              >
                                                {revokingPermissionId === permission.id ? 'Revoking…' : 'Revoke'}
                                              </button>
                                            )}
                                          </div>
                                        )
                                      })
                                    )}
                                  </div>
                                )}
                              </div>
                            )}
                          </>
                        )}
                          </div>
                          {document.id != null && (
                            <button
                              className="button button-outline"
                              onClick={() => handleDownload(document)}
                            >
                              Download
                            </button>
                          )}

                        </div>
                      ))}
                    </div>
                  )}
                </article>
              </>
            ) : (
              <article className="panel empty-state">
                <strong>Sign in to manage documents</strong>
                <p>Your document list requires an authenticated session.</p>
                <button className="button button-primary" onClick={() => setAuthMode('login')}>
                  Sign in
                </button>
              </article>
            )}
          </section>
        )}

        {activeSection === 'Audit trail' && (
          <section className="content-section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">SECURITY MONITORING</span>
                <h2>Audit trail</h2>
              </div>
              <button
                className="button button-outline"
                onClick={loadDashboardData}
                disabled={dataLoading || !isSignedIn}
              >
                {dataLoading ? 'Refreshing…' : 'Refresh events'}
              </button>
            </div>

            <article className="panel">
              {!isSignedIn ? (
                <div className="empty-state">
                  <strong>Sign in to view audit events</strong>
                  <button className="button button-primary" onClick={() => setAuthMode('login')}>
                    Sign in
                  </button>
                </div>
              ) : auditEvents.length === 0 ? (
                <div className="empty-state">
                  <strong>No audit events returned</strong>
                  <p>The API did not return any events for this account.</p>
                </div>
              ) : (
                <div className="live-list">
                  {auditEvents.map((event, index) => (
                    <div className="activity-row" key={event.id ?? index}>
                      <span className="activity-icon">◷</span>
                      <div>
                        <strong>{getAuditDescription(event)}</strong>
                        <p>
                          {formatDate(
                            event.created_at || event.timestamp || event.occurred_at
                          )}
                        </p>
                        {event.ip_address && <p>IP address: {event.ip_address}</p>}
                        {event.document_id != null && (
                          <p>Document ID: {event.document_id}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </article>
          </section>
        )}
{activeSection === 'Shared with me' && (
  <section className="content-section">
    <div className="section-heading">
      <div>
        <span className="eyebrow">DOCUMENT ACCESS</span>
        <h2>Shared with me</h2>
      </div>
    </div>
    {!isSignedIn ? (
      <article className="panel empty-state">
        <strong>Sign in to view shared documents</strong>
        <button
          className="button button-primary"
          onClick={() => setAuthMode('login')}
        >
          Sign in
        </button>
      </article>
    ) : sharedDocuments.length === 0 ? (
      <article className="panel empty-state">
        <strong>No documents have been shared with you yet</strong>
        <p>
          Documents shared with your account will appear here.
        </p>
        <button
          className="button button-outline"
          onClick={() => selectSection('Documents')}
        >
          Go to documents
        </button>
      </article>
    ) : (
      <div className="document-grid">
        {sharedDocuments.map(document => (
          <article className="panel" key={document.id}>
            <span className="eyebrow">SHARED DOCUMENT</span>
            <h3>{document.title}</h3>
            <p>Document ID: {document.id}</p>
            <p>Owner ID: {document.owner_id}</p>
            {document.created_at && (
              <p>Added: {formatDate(document.created_at)}</p>
            )}
          </article>
        ))}
      </div>
    )}
  </section>
)}
{activeSection === 'Incidents' && (
  <section className="content-section">
    <div className="section-heading">
      <div>
        <span className="eyebrow">SECURITY RESPONSE</span>
        <h2>Incidents</h2>
      </div>
      <button
        className="button button-outline"
        onClick={loadIncidents}
      >
        Refresh
      </button>
        </div>

    <article className="panel">
      <h3>Report a security incident</h3>
      <p>Record a security concern associated with a document.</p>

      <form onSubmit={handleCreateIncident}>
        <label htmlFor="incident-document-id">Document ID</label>
        <input
          id="incident-document-id"
          type="number"
          min="1"
          required
          value={incidentDocumentId}
          onChange={(event) => setIncidentDocumentId(event.target.value)}
          placeholder="Enter document ID"
        />

        <label htmlFor="incident-description">Incident description</label>
        <textarea
          id="incident-description"
          required
          minLength="5"
          maxLength="5000"
          value={incidentDescription}
          onChange={(event) => setIncidentDescription(event.target.value)}
          placeholder="Describe the security incident"
          rows="4"
        />

        <button
          className="button"
          type="submit"
          disabled={incidentSubmitting}
        >
          {incidentSubmitting ? 'Reporting...' : 'Report incident'}
        </button>
      </form>
    </article>

    {incidentsError && (
      <article className="panel">
        <strong>Unable to load incidents</strong>
        <p>{incidentsError}</p>
      </article>
    )}

    {incidentsLoading && (
      <article className="panel">
        <p>Loading incidents...</p>
      </article>
    )}

    {!incidentsLoading && !incidentsError && incidents.length === 0 && (
      <article className="panel empty-state">
        <strong>No incidents recorded</strong>
        <p>There are currently no incident records to display.</p>
      </article>
    )}

    {!incidentsLoading && !incidentsError && incidents.length > 0 && (
      <div className="document-grid">
        {incidents.map((incident) => (
          <article className="panel" key={incident.id}>
            <div className="section-heading">
              <strong>Incident #{incident.id}</strong>
              <span className="status-badge">
                {incident.status}
              </span>
            </div>

            <p>{incident.description}</p>

            <div className="document-meta">
              <span>Document ID: {incident.document_id}</span>
              <span>Reported by: {incident.reported_by}</span>
              <span>
                Detected:{' '}
                {incident.detected_at
                  ? new Date(incident.detected_at).toLocaleString()
                  : 'Unknown'}
              </span>
            </div>
          </article>
        ))}
      </div>
    )}
  </section>
)}

        {notice && (
          <div className="notice" role="status">
            <span>{notice}</span>
            <button onClick={() => setNotice('')}>Dismiss ×</button>
          </div>
        )}

        <footer>
          © 2026 TrustVault
          <span>Secure document management · Built for trust</span>
        </footer>
      </main>

      {authMode && (
        <div className="modal-backdrop" onClick={() => setAuthMode('')}>
          <section className="auth-modal" onClick={event => event.stopPropagation()}>
            <button
              className="modal-close"
              type="button"
              onClick={() => setAuthMode('')}
            >
              ×
            </button>

            <div className="modal-brand">◈ TrustVault</div>
            <h2>
              {authMode === 'login' ? 'Welcome back' : 'Create your account'}
            </h2>
            <p>
              {authMode === 'login'
                ? 'Sign in to access your secure workspace.'
                : 'Get started with your secure document workspace.'}
            </p>

            <form className="auth-form" onSubmit={handleAuth}>
              {authMode === 'register' && (
                <label>
                  Full name
                  <input
                    name="name"
                    placeholder="Your full name"
                    autoComplete="name"
                    required
                  />
                </label>
              )}

              <label>
                Email address
                <input
                  name="email"
                  type="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </label>

              <label>
                Password
                <input
                  name="password"
                  type="password"
                  placeholder="Enter your password"
                  autoComplete={
                    authMode === 'login' ? 'current-password' : 'new-password'
                  }
                  minLength={8}
                  required
                />
              </label>

              <button
                className="button button-primary submit-button"
                type="submit"
                disabled={isLoading}
              >
                {isLoading
                  ? 'Please wait…'
                  : authMode === 'login'
                    ? 'Sign in securely →'
                    : 'Create account →'}
              </button>
            </form>

            <div className="switch-auth">
              {authMode === 'login'
                ? 'New to TrustVault?'
                : 'Already have an account?'}{' '}
              <button
                type="button"
                onClick={() => {
                  setNotice('')
                  setAuthMode(authMode === 'login' ? 'register' : 'login')
                }}
              >
                {authMode === 'login' ? 'Create account' : 'Sign in'}
              </button>
            </div>

            <div className="modal-security">
              ✓ Your account is protected by access controls
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default App
