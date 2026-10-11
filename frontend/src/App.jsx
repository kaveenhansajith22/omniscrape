
import { useState } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [websiteUrl, setWebsiteUrl] = useState(
    'https://books.toscrape.com/catalogue/page-1.html',
  )
  const [maxPages, setMaxPages] = useState('1')
  const [exportFormat, setExportFormat] = useState('CSV')
  const [activeNav, setActiveNav] = useState('New scrape')
  const [results, setResults] = useState([])
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [stats, setStats] = useState(null)

  async function handleScrape(event) {
    event.preventDefault()
    setError('')
    setStats(null)

    let parsedUrl

    try {
      parsedUrl = new URL(websiteUrl)
    } catch {
      setError('Please enter a valid website URL.')
      return
    }

    if (parsedUrl.protocol !== 'https:') {
      setError('Please enter a valid HTTPS website URL.')
      return
    }

    if (parsedUrl.hostname !== 'books.toscrape.com') {
      setError(
        'This first integration supports books.toscrape.com only. Other websites need their own extraction configuration.',
      )
      return
    }

    setStatus('loading')
    setResults([])

    try {
      const response = await fetch(`${API_URL}/api/scrape`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: websiteUrl,
          max_pages: Number(maxPages),
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'The scraping request failed.')
      }

      setResults(data.items || [])
      setStats({
        pagesCrawled: data.pages_crawled,
        itemsCount: data.items_count,
        errors: data.errors,
        duplicatesDropped: data.duplicates_dropped,
      })
      setStatus('success')
    } catch (err) {
      setStatus('error')
      setError(
        err instanceof TypeError
          ? 'Cannot connect to the backend. Make sure the FastAPI server is running on port 8000.'
          : err.message || 'Something went wrong while scraping.',
      )
    }
  }

  function handleReset() {
    setWebsiteUrl('')
    setResults([])
    setStats(null)
    setStatus('idle')
    setError('')
  }

  function handleExport() {
    if (results.length === 0) return

    const content =
      exportFormat === 'JSON'
        ? JSON.stringify(results, null, 2)
        : [
            Object.keys(results[0])
              .map(escapeCsv)
              .join(','),
            ...results.map((row) =>
              Object.values(row).map(escapeCsv).join(','),
            ),
          ].join('\n')

    const mimeType =
      exportFormat === 'JSON'
        ? 'application/json'
        : 'text/csv;charset=utf-8;'

    const extension = exportFormat === 'JSON' ? 'json' : 'csv'
    const blob = new Blob([content], { type: mimeType })
    const downloadUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = downloadUrl
    link.download = `omniscrape-results.${extension}`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(downloadUrl)
  }

  function escapeCsv(value) {
    const text =
      value !== null && typeof value === 'object'
        ? JSON.stringify(value)
        : String(value ?? '')

    return `"${text.replaceAll('"', '""')}"`
  }

  function getRating(value) {
    if (!value) return '—'

    const ratingClasses = {
      One: '1 / 5',
      Two: '2 / 5',
      Three: '3 / 5',
      Four: '4 / 5',
      Five: '5 / 5',
    }

    if (Array.isArray(value)) {
      return value
        .map((part) => ratingClasses[part] || part)
        .join(', ')
    }

    return ratingClasses[value] || value
  }

  const isLoading = status === 'loading'
  const isConnected = status === 'success'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#dashboard">
          <span className="brand-mark">
            <span />
            <span />
            <span />
            <span />
          </span>
          <span>
            Omni<span className="brand-light">Scrape</span>
          </span>
        </a>

        <div className="workspace-label">WORKSPACE</div>

        <nav className="navigation" aria-label="Main navigation">
          {['New scrape', 'History', 'Exports'].map((item) => (
            <button
              key={item}
              className={
                activeNav === item ? 'nav-item active' : 'nav-item'
              }
              onClick={() => setActiveNav(item)}
            >
              <span className="nav-icon">
                {item === 'New scrape'
                  ? '⌘'
                  : item === 'History'
                    ? '◷'
                    : '⇩'}
              </span>
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="plan-card">
            <div className="plan-icon">✳</div>
            <p className="plan-title">Your workspace</p>
            <p className="plan-description">
              Your scraping tools, all in one place.
            </p>
            <div className="plan-status">
              <span className="status-dot" />
              Local development
            </div>
          </div>

          <div className="profile">
            <div className="avatar">K</div>
            <div className="profile-info">
              <strong>Workspace user</strong>
              <span>Free workspace</span>
            </div>
            <span className="profile-menu">···</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> <strong>{activeNav}</strong>
          </div>
          <div className="topbar-right">
            <span className="connection-indicator">
              <span className="status-dot" />
              {isConnected ? 'API connected' : 'Local API'}
            </span>
            <button
              className="help-button"
              onClick={() =>
                window.alert(
                  'OmniScrape uses its Python API to collect and return website data.',
                )
              }
            >
              ? <span>Help</span>
            </button>
          </div>
        </header>

        <div className="page-content">
          <section className="welcome-section">
            <div>
              <div className="eyebrow">
                <span className="eyebrow-line" />
                WEB DATA EXTRACTION
              </div>
              <h1>
                Turn websites into <span>data.</span>
              </h1>
              <p className="welcome-description">
                Configure a scrape, collect the information you need,
                and export it in seconds.
              </p>
            </div>
            <div className="hero-decoration" aria-hidden="true">
              <div className="decoration-orbit orbit-one" />
              <div className="decoration-orbit orbit-two" />
              <div className="decoration-center">{'{ }'}</div>
              <div className="decoration-dot dot-one" />
              <div className="decoration-dot dot-two" />
            </div>
          </section>

          <section className="stats-grid" aria-label="Scraping statistics">
            <article className="stat-card">
              <div className="stat-top">
                <span>Total records</span>
                <span className="stat-icon purple">▤</span>
              </div>
              <strong>{results.length}</strong>
              <p>Real records returned by the API</p>
            </article>

            <article className="stat-card">
              <div className="stat-top">
                <span>Scrape status</span>
                <span className="stat-icon green">
                  {isLoading ? '…' : isConnected ? '✓' : '○'}
                </span>
              </div>
              <strong className="stat-status">
                {isLoading
                  ? 'Running'
                  : isConnected
                    ? 'Success'
                    : status === 'error'
                      ? 'Failed'
                      : 'Ready'}
              </strong>
              <p>
                {isLoading
                  ? 'Collecting website data'
                  : isConnected
                    ? 'Scrape completed'
                    : 'Ready to configure'}
              </p>
            </article>

            <article className="stat-card">
              <div className="stat-top">
                <span>Export format</span>
                <span className="stat-icon orange">⇩</span>
              </div>
              <strong>{exportFormat}</strong>
              <p>Choose your output format</p>
            </article>
          </section>

          <section className="content-grid">
            <article className="panel scrape-panel">
              <div className="panel-heading">
                <div>
                  <div className="section-number">01 / CONFIGURATION</div>
                  <h2>New scraping job</h2>
                  <p>Tell OmniScrape what you want to collect.</p>
                </div>
                <span className="panel-symbol">↗</span>
              </div>

              <form onSubmit={handleScrape}>
                <label htmlFor="website-url">Website URL</label>
                <div className="url-input-wrap">
                  <span className="input-prefix">↗</span>
                  <input
                    id="website-url"
                    type="url"
                    placeholder="https://books.toscrape.com"
                    value={websiteUrl}
                    onChange={(event) =>
                      setWebsiteUrl(event.target.value)
                    }
                    required
                  />
                </div>
                <p className="field-hint">
                  Current integration: books.toscrape.com
                </p>

                <div className="form-row">
                  <div className="form-field">
                    <label htmlFor="max-pages">Maximum pages</label>
                    <select
                      id="max-pages"
                      value={maxPages}
                      onChange={(event) =>
                        setMaxPages(event.target.value)
                      }
                    >
                      <option value="1">1 page</option>
                      <option value="3">3 pages</option>
                      <option value="5">5 pages</option>
                    </select>
                  </div>

                  <div className="form-field">
                    <label htmlFor="export-format">Export format</label>
                    <select
                      id="export-format"
                      value={exportFormat}
                      onChange={(event) =>
                        setExportFormat(event.target.value)
                      }
                    >
                      <option value="CSV">CSV spreadsheet</option>
                      <option value="JSON">JSON data</option>
                    </select>
                  </div>
                </div>

                {error && (
                  <p className="error-message" role="alert">
                    {error}
                  </p>
                )}

                {isConnected && (
                  <div className="demo-notice">
                    <span>✓</span>
                    Live scrape completed. These results came from the
                    Python API.
                  </div>
                )}

                <div className="form-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={handleReset}
                    disabled={isLoading}
                  >
                    Reset
                  </button>
                  <button
                    className="primary-button"
                    type="submit"
                    disabled={isLoading}
                  >
                    <span>{isLoading ? '…' : '▶'}</span>
                    {isLoading ? 'Scraping…' : 'Scrape website'}
                  </button>
                </div>
              </form>
            </article>

            <article className="panel guide-panel">
              <div className="section-number">HOW IT WORKS</div>
              <h2>From URL to data</h2>
              <p className="guide-description">
                A simple workflow for extracting structured website data.
              </p>

              <div className="workflow">
                <div className="workflow-step">
                  <div className="workflow-icon purple">↗</div>
                  <div>
                    <strong>Enter a URL</strong>
                    <p>Choose the supported website to collect data from.</p>
                  </div>
                </div>
                <div className="workflow-connector" />
                <div className="workflow-step">
                  <div className="workflow-icon blue">⌘</div>
                  <div>
                    <strong>Scrape with Python</strong>
                    <p>FastAPI runs your existing OmniScrape engine.</p>
                  </div>
                </div>
                <div className="workflow-connector" />
                <div className="workflow-step">
                  <div className="workflow-icon green">⇩</div>
                  <div>
                    <strong>Preview and export</strong>
                    <p>Inspect real records and download your data.</p>
                  </div>
                </div>
              </div>

              <div className="engine-note">
                <span className="engine-indicator" />
                <div>
                  <strong>OmniScrape engine</strong>
                  <p>Python-powered scraping · API integration</p>
                </div>
              </div>
            </article>
          </section>

          <section className="panel results-panel">
            <div className="results-heading">
              <div>
                <div className="section-number">02 / OUTPUT</div>
                <h2>Data preview</h2>
                <p>
                  {results.length > 0
                    ? `${results.length} real records returned`
                    : 'Your extracted records will appear here.'}
                </p>
              </div>
              <button
                className="export-button"
                onClick={handleExport}
                disabled={results.length === 0}
              >
                ↓ <span>Export {exportFormat}</span>
              </button>
            </div>

            {stats && (
              <div className="table-footer">
                <span>Pages crawled: {stats.pagesCrawled}</span>
                <span>Items: {stats.itemsCount}</span>
                <span>Errors: {stats.errors}</span>
                <span>Duplicates: {stats.duplicatesDropped}</span>
              </div>
            )}

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>PRODUCT TITLE</th>
                    <th>PRICE</th>
                    <th>AVAILABILITY</th>
                    <th>RATING</th>
                    <th>STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  {results.length > 0 ? (
                    results.map((item, index) => (
                      <tr key={`${item.title || 'item'}-${index}`}>
                        <td>
                          <span className="row-number">
                            {String(index + 1).padStart(2, '0')}
                          </span>
                          <strong>{item.title || 'Untitled'}</strong>
                        </td>
                        <td className="price-cell">
                          {item.price ?? '—'}
                        </td>
                        <td>
                          <span className="availability">
                            <span className="status-dot" />
                            {item.availability || '—'}
                          </span>
                        </td>
                        <td>{getRating(item.rating)}</td>
                        <td>
                          <span className="result-badge">Live data</span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="5" className="empty-state">
                        <div className="empty-icon">⌘</div>
                        <strong>
                          {isLoading
                            ? 'Scraping website…'
                            : 'No records to display'}
                        </strong>
                        <p>
                          {isLoading
                            ? 'Please wait while OmniScrape collects data.'
                            : 'Run a scraping job to see real website data here.'}
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="table-footer">
              <span>
                Showing {results.length} records
              </span>
              <span className="preview-label">
                <span className="status-dot" />
                {isConnected ? 'Live results' : 'Awaiting results'}
              </span>
            </div>
          </section>

          <footer className="page-footer">
            <span>
              OMNISCRAPE <span className="footer-separator">/</span> WEB DATA
              TOOLKIT
            </span>
            <span>Built for structured data extraction.</span>
          </footer>
        </div>
      </main>
    </div>
  )
}

export default App