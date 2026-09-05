import './App.css'

const stats = [
  { label: 'TOTAL ROADS', value: '101', meta: 'Network monitored' },
  { label: 'AVAILABLE', value: '97', meta: '95.9% operational' },
  { label: 'BLOCKED', value: '04', meta: 'Requires attention', danger: true },
  { label: 'ACTIVE VEHICLES', value: '238', meta: 'Fleet connected' },
]

const incidents = [
  {
    type: 'LANDSLIDE',
    road: 'R00029',
    location: 'NH-16 · Sikkim Sector',
    time: '2 min ago',
    severity: 'HIGH',
  },
  {
    type: 'FLOOD',
    road: 'R00037',
    location: 'NH-10 · Siliguri Sector',
    time: '8 min ago',
    severity: 'HIGH',
  },
  {
    type: 'HEAVY RAIN',
    road: 'R00041',
    location: 'NH-31 · Guwahati Sector',
    time: '16 min ago',
    severity: 'MEDIUM',
  },
]

function App() {
  return (
    <div className="dashboard">

      {/* HEADER */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">NR</div>

          <div>
            <p className="eyebrow">NER-RESQ · OPERATIONS</p>
            <h1>Smart Logistics Command Center</h1>
            <p className="subtitle">
              Emergency logistics & road risk intelligence
            </p>
          </div>
        </div>

        <div className="header-right">
          <div className="last-sync">
            <span className="sync-dot"></span>
            Last sync: just now
          </div>

          <div className="system-status">
            <span className="status-dot"></span>
            SYSTEM OPERATIONAL
          </div>
        </div>
      </header>

      {/* KPI STATS */}
      <section className="stats-grid">
        {stats.map((stat) => (
          <div className={`stat-card ${stat.danger ? 'stat-danger' : ''}`} key={stat.label}>
            <div className="stat-top">
              <span className="stat-label">{stat.label}</span>
              <span className="stat-indicator"></span>
            </div>

            <strong>{stat.value}</strong>

            <span className="stat-meta">{stat.meta}</span>
          </div>
        ))}
      </section>

      {/* MAIN CONTENT */}
      <main className="main-grid">

        {/* LIVE MAP */}
        <section className="map-card">
          <div className="section-header">
            <div>
              <span className="section-kicker">REAL-TIME NETWORK</span>
              <h2>Live Operations Map</h2>
            </div>

            <div className="map-controls">
              <button className="map-control active">LIVE</button>
              <button className="map-control">ROADS</button>
              <button className="map-control">VEHICLES</button>
            </div>
          </div>

          <div className="map-area">

            <div className="map-grid"></div>

            {/* Map labels */}
            <span className="map-region region-one">SIKKIM</span>
            <span className="map-region region-two">ASSAM</span>
            <span className="map-region region-three">MEGHALAYA</span>

            {/* Roads */}
            <div className="road road-one"></div>
            <div className="road road-two"></div>
            <div className="road road-three"></div>
            <div className="road road-four"></div>
            <div className="road road-five"></div>

            {/* Selected road */}
            <div className="selected-road-line"></div>

            {/* Road markers */}
            <div className="map-marker marker-green marker-one">
              <span></span>
              R00039
            </div>

            <div className="map-marker marker-red marker-two">
              <span></span>
              R00029
            </div>

            <div className="map-marker marker-orange marker-three">
              <span></span>
              R00037
            </div>

            {/* Vehicles */}
            <div className="vehicle vehicle-one">
              <span className="vehicle-icon">V</span>
              <small>V102</small>
            </div>

            <div className="vehicle vehicle-two">
              <span className="vehicle-icon">V</span>
              <small>V117</small>
            </div>

            <div className="vehicle vehicle-three">
              <span className="vehicle-icon">V</span>
              <small>V204</small>
            </div>

            {/* Incident markers */}
            <div className="incident-marker incident-one">!</div>
            <div className="incident-marker incident-two">!</div>

            {/* Map center label */}
            <div className="map-center-info">
              <span>NETWORK STATUS</span>
              <strong>97 / 101</strong>
              <small>ROADS AVAILABLE</small>
            </div>

            <div className="map-live-label">
              <span className="status-dot"></span>
              LIVE TELEMETRY
            </div>
          </div>

          <div className="map-footer">

            <div className="map-legend">
              <span>
                <i className="legend-dot available"></i>
                Available
              </span>

              <span>
                <i className="legend-dot selected"></i>
                Selected
              </span>

              <span>
                <i className="legend-dot blocked"></i>
                Incident
              </span>

              <span>
                <i className="legend-vehicle">V</i>
                Vehicle
              </span>
            </div>

            <span className="map-update">
              Auto-refresh enabled
            </span>

          </div>
        </section>

        {/* RIGHT SIDE */}
        <aside className="side-column">

          {/* LIVE INCIDENTS */}
          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="section-kicker">ALERT CENTER</span>
                <h2>Live Incidents</h2>
              </div>

              <span className="alert-count">03</span>
            </div>

            <div className="incident-list">

              {incidents.map((incident) => (
                <div className="incident-row" key={incident.road}>

                  <div className={`incident-icon ${incident.severity.toLowerCase()}`}>
                    !
                  </div>

                  <div className="incident-info">
                    <div className="incident-title">
                      <strong>{incident.type}</strong>
                      <span className={`severity ${incident.severity.toLowerCase()}`}>
                        {incident.severity}
                      </span>
                    </div>

                    <span>{incident.road} · {incident.location}</span>
                    <small>{incident.time}</small>
                  </div>

                </div>
              ))}

            </div>

            <button className="view-all">
              View all incidents <span>→</span>
            </button>
          </section>

          {/* SELECTED ROAD */}
          <section className="panel selected-road-panel">

            <div className="panel-header">
              <div>
                <span className="section-kicker">ROAD INTELLIGENCE</span>
                <h2>Selected Road</h2>
              </div>

              <span className="road-status">
                MONITORED
              </span>
            </div>

            <div className="road-id">
              <span>ROAD ID</span>
              <strong>R00040</strong>
            </div>

            <div className="road-metrics">

              <div>
                <span>RISK LEVEL</span>
                <strong className="medium-risk">MEDIUM</strong>
              </div>

              <div>
                <span>VEHICLES</span>
                <strong>11</strong>
              </div>

              <div>
                <span>TRAFFIC</span>
                <strong>62%</strong>
              </div>

            </div>

            <div className="risk-bar">
              <div className="risk-bar-label">
                <span>Current risk index</span>
                <strong>58 / 100</strong>
              </div>

              <div className="risk-track">
                <div className="risk-fill"></div>
              </div>
            </div>

          </section>

        </aside>
      </main>

      {/* INTELLIGENCE CARDS */}
      <section className="intelligence-section">

        <div className="section-heading">
          <div>
            <span className="section-kicker">DECISION SUPPORT</span>
            <h2>Operations Intelligence</h2>
          </div>

          <span className="section-note">
            Powered by NER-RESQ intelligence modules
          </span>
        </div>

        <div className="feature-grid">

          {/* FIELD REPORT */}
          <button className="feature-card">

            <div className="feature-icon report-icon">
              +
            </div>

            <div className="feature-content">
              <span className="feature-label">FIELD OPERATIONS</span>
              <strong>Field Officer Report</strong>
              <p>Submit real-time ground intelligence</p>
            </div>

            <span className="arrow">→</span>

          </button>

          {/* WEATHER */}
          <button className="feature-card">

            <div className="feature-icon weather-icon">
              ~
            </div>

            <div className="feature-content">
              <span className="feature-label">ENVIRONMENT</span>
              <strong>Weather Intelligence</strong>
              <p>Monitor conditions affecting routes</p>
            </div>

            <span className="arrow">→</span>

          </button>

          {/* ML */}
          <button className="feature-card ml-card">

            <div className="feature-icon ml-icon">
              AI
            </div>

            <div className="feature-content">
              <span className="feature-label">PREDICTIVE ANALYTICS</span>
              <strong>ML Road Risk</strong>
              <p>AI-powered risk prediction & analysis</p>
            </div>

            <div className="ml-score">
              <strong>72%</strong>
              <span>RISK</span>
            </div>

          </button>

          {/* ROUTE */}
          <button className="feature-card">

            <div className="feature-icon route-icon">
              ↗
            </div>

            <div className="feature-content">
              <span className="feature-label">ROUTE OPTIMIZATION</span>
              <strong>Route / Reroute</strong>
              <p>Find safer and faster alternatives</p>
            </div>

            <span className="arrow">→</span>

          </button>

        </div>
      </section>

      {/* QUICK ACTIONS */}
      <section className="quick-actions">

        <div>
          <span className="section-kicker">QUICK ACTIONS</span>
          <h2>Command Center</h2>
        </div>

        <div className="action-buttons">
          <button>+ Report Incident</button>
          <button>⌁ Check Weather</button>
          <button>↗ Calculate Route</button>
        </div>

      </section>

      {/* FOOTER */}
      <footer>
        <span>NER-RESQ</span>
        <span>Smart Emergency Logistics & Road Risk Intelligence</span>
        <span>Command Center v1.0</span>
      </footer>

    </div>
  )
}

export default App