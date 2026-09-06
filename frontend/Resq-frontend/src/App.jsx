import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function App() {
  const [token, setToken] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [dashboard, setDashboard] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [locations, setLocations] = useState([])
  const [mlStatus, setMlStatus] = useState(null)
  const [lastSync, setLastSync] = useState(null)

  // DEMO GPS SIMULATION
  // Uses the real backend GPS endpoint to move a selected vehicle along the
  // planned GIS route. This is explicitly labelled as simulation in the UI.
  const [simulationVehicleId, setSimulationVehicleId] = useState('')
  const [simulationRunning, setSimulationRunning] = useState(false)
  const [simulationProgress, setSimulationProgress] = useState(0)
  const [simulationSpeed, setSimulationSpeed] = useState(45)
  const [simulationMessage, setSimulationMessage] = useState('')
  const [simulationError, setSimulationError] = useState('')
  const simulationTimerRef = useRef(null)
  const simulationIndexRef = useRef(0)
  const simulationRequestRef = useRef(false)

  const mapRef = useRef(null)
  const leafletMapRef = useRef(null)
  const leafletLayerRef = useRef(null)

  const [from, setFrom] = useState('Tawang')
  const [to, setTo] = useState('Itanagar')

  const [route, setRoute] = useState(null)
  const [routeLoading, setRouteLoading] = useState(false)
  const [routeError, setRouteError] = useState('')
  const [incidentRouteStatus, setIncidentRouteStatus] = useState('')
  const autoIncidentRouteRef = useRef('')
  const [gisRoute, setGisRoute] = useState(null)
  const [gisRouteLoading, setGisRouteLoading] = useState(false)
  const [gisRouteError, setGisRouteError] = useState('')

  const [weather, setWeather] = useState(null)
  const [showWeather, setShowWeather] = useState(false)

  // REFRESH DATA
  const [refreshLoading, setRefreshLoading] = useState(false)
  const [refreshMessage, setRefreshMessage] = useState('')
  const [refreshError, setRefreshError] = useState('')

  // INCIDENT FORM
  const [showIncidentForm, setShowIncidentForm] = useState(false)
  const [showReports, setShowReports] = useState(false)
  const [incidentLoading, setIncidentLoading] = useState(false)
  const [incidentMessage, setIncidentMessage] = useState('')
  const [incidentError, setIncidentError] = useState('')

  const [incidentForm, setIncidentForm] = useState({
    incident_type: 'ROAD BLOCKAGE',
    severity: 'HIGH',
    location: '',
    road_id: '',
    description: '',
    latitude: '',
    longitude: '',
  })

  // VEHICLE REGISTRATION
  const [showVehicleForm, setShowVehicleForm] = useState(false)
  const [vehicleLoading, setVehicleLoading] = useState(false)
  const [vehicleMessage, setVehicleMessage] = useState('')
  const [vehicleError, setVehicleError] = useState('')

  const [vehicleForm, setVehicleForm] = useState({
    vehicle_type: 'RESCUE TRUCK',
    driver_name: '',
    cargo_type: '',
    current_location: '',
    latitude: '',
    longitude: '',
    current_road_id: '',
    speed: '',
  })

  async function loadData(accessToken, weatherLocation = 'Tawang') {
    if (!accessToken) {
      throw new Error('No authentication token available.')
    }

    const headers = {
      Authorization: `Bearer ${accessToken}`,
    }

    const requests = [
      {
        name: 'dashboard',
        request: fetch(`${API_BASE_URL}/api/dashboard`, {
          headers,
        }),
      },
      {
        name: 'incidents',
        request: fetch(`${API_BASE_URL}/api/incidents`, {
          headers,
        }),
      },
      {
        name: 'vehicles',
        request: fetch(`${API_BASE_URL}/api/vehicles`, {
          headers,
        }),
      },
      {
        name: 'locations',
        request: fetch(`${API_BASE_URL}/api/locations`, {
          headers,
        }),
      },
      {
        name: 'weather',
        request: fetch(
          `${API_BASE_URL}/api/weather?location=${encodeURIComponent(weatherLocation)}`,
          {
            headers,
          },
        ),
      },
      {
        name: 'mlStatus',
        request: fetch(`${API_BASE_URL}/api/ml/status`, {
          headers,
        }),
      },
    ]

    const results = await Promise.allSettled(
      requests.map((item) => item.request),
    )

    const failures = []

    for (let index = 0; index < results.length; index += 1) {
      const result = results[index]
      const name = requests[index].name

      if (result.status === 'rejected') {
        failures.push(`${name}: ${result.reason?.message || 'request failed'}`)
        continue
      }

      const response = result.value

      if (!response.ok) {
        let detail = `HTTP ${response.status}`

        try {
          const errorData = await response.json()
          detail =
            errorData?.detail ||
            errorData?.message ||
            detail
        } catch {
          // Keep the HTTP status when the response is not JSON.
        }

        failures.push(`${name}: ${detail}`)
        continue
      }

      try {
        const data = await response.json()

        if (!data?.success) {
          failures.push(
            `${name}: ${data?.message || 'API returned an unsuccessful response'}`,
          )
          continue
        }

        if (name === 'dashboard') {
          setDashboard(data.data)
        }

        if (name === 'incidents') {
          setIncidents(data.data || [])
        }

        if (name === 'vehicles') {
          setVehicles(data.data || [])
        }

        if (name === 'locations') {
          setLocations(data.data || [])
        }

        if (name === 'weather') {
          setWeather(data.data)
        }

        if (name === 'mlStatus') {
          setMlStatus(data.data)
        }
      } catch (error) {
        failures.push(
          `${name}: ${error.message || 'invalid response'}`,
        )
      }
    }

    if (failures.length === 0) {
      setLastSync(new Date())
    }

    if (failures.length > 0) {
      throw new Error(
        `Some data could not be refreshed: ${failures.join(' | ')}`,
      )
    }
  }

  // LIVE OPERATIONAL CONTEXT
  // These values are derived from backend data instead of hardcoded dashboard values.
  const activeIncidents = incidents.filter(
    (item) => String(item?.status || 'ACTIVE').toUpperCase() !== 'RESOLVED',
  )

  const primaryIncident = activeIncidents[0] || null
  const selectedRoad =
    primaryIncident?.road_id ||
    vehicles[0]?.current_road_id ||
    'NETWORK'

  const selectedLocation =
    primaryIncident?.location ||
    vehicles[0]?.current_location ||
    'Tawang'

  const roadStatus = primaryIncident
    ? String(primaryIncident.severity || '').toUpperCase() === 'CRITICAL'
      ? 'CRITICAL'
      : String(primaryIncident.severity || '').toUpperCase() === 'HIGH'
        ? 'BLOCKED'
        : 'AT RISK'
    : 'CLEAR'

  const roadStatusClass = roadStatus === 'CLEAR' ? '' : 'red'

  const activeHighPriorityIncidents = activeIncidents.filter((item) =>
    ['HIGH', 'CRITICAL'].includes(
      String(item?.severity || '').toUpperCase(),
    ),
  )

  const activeVehicleCount = vehicles.filter((item) =>
    String(item?.status || '').toUpperCase() !== 'OFFLINE',
  ).length

  const liveVehicles = vehicles.filter((item) => {
    const status = String(item?.status || '').toUpperCase()
    return status !== 'OFFLINE'
  })

  function formatGpsUpdate(value) {
    if (!value) return 'GPS UPDATE UNAVAILABLE'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return String(value)
    return date.toLocaleString()
  }

  function vehicleStatusLabel(value) {
    const status = String(value || 'UNKNOWN').toUpperCase()
    if (status === 'AVAILABLE') return 'AVAILABLE'
    if (status === 'IN_TRANSIT') return 'IN TRANSIT'
    if (status === 'OFFLINE') return 'OFFLINE'
    return status.replaceAll('_', ' ')
  }

  // ROUTE LOCATIONS: build the planner choices from the live backend network.
  const routeLocationOptions = locations
    .map((item, index) => {
      const value =
        item?.location_id ??
        item?.node_id ??
        item?.id ??
        item?.name ??
        item?.location_name ??
        item?.location ??
        item?.city

      const label =
        item?.name ??
        item?.location_name ??
        item?.location ??
        item?.city ??
        item?.location_id ??
        item?.node_id ??
        item?.id ??
        `Network location ${index + 1}`

      if (value === undefined || value === null || String(value).trim() === '') {
        return null
      }

      return {
        value: String(value),
        label: String(label),
      }
    })
    .filter(Boolean)
    .filter(
      (option, index, options) =>
        options.findIndex((item) => item.value === option.value) === index,
    )

  const routeLocationValues = routeLocationOptions.map((item) => item.value)

  useEffect(() => {
    if (routeLocationOptions.length === 0) return

    const vehicleLocation = String(
      vehicles[0]?.current_location || '',
    ).trim()

    const incidentLocation = String(
      primaryIncident?.location || '',
    ).trim()

    const preferredFrom =
      [vehicleLocation, incidentLocation].find((candidate) =>
        routeLocationValues.includes(candidate),
      ) || routeLocationOptions[0].value

    const preferredDestination =
      routeLocationOptions.find(
        (option) =>
          option.label.toLowerCase() === 'itanagar' ||
          option.value.toLowerCase() === 'itanagar',
      )?.value ||
      routeLocationOptions.find(
        (option) => option.value !== preferredFrom,
      )?.value ||
      preferredFrom

    setFrom((current) =>
      routeLocationValues.includes(current) ? current : preferredFrom,
    )

    setTo((current) =>
      routeLocationValues.includes(current) && current !== preferredFrom
        ? current
        : preferredDestination,
    )
  }, [locations, vehicles, primaryIncident])

  const availableVehicleCount = vehicles.filter((item) =>
    String(item?.status || '').toUpperCase() === 'AVAILABLE',
  ).length

  const mlStatusText = String(
    mlStatus?.status ??
      mlStatus?.state ??
      mlStatus?.message ??
      mlStatus?.data?.status ??
      '',
  ).trim().toUpperCase()

  const mlReady =
    mlStatus?.ready === true ||
    mlStatus?.data?.ready === true ||
    ['READY', 'ONLINE', 'AVAILABLE', 'ACTIVE', 'RUNNING'].includes(
      mlStatusText,
    )

  async function refreshData() {
    if (!token) {
      setRefreshError('Connecting to backend...')
      setRefreshMessage('')
      return
    }

    setRefreshLoading(true)
    setRefreshMessage('')
    setRefreshError('')

    try {
      await loadData(token, selectedLocation)
      setRefreshMessage('Data refreshed successfully.')

      window.setTimeout(() => {
        setRefreshMessage('')
      }, 1800)
    } catch (error) {
      console.error('Refresh data error:', error)
      setRefreshError(
        error.message || 'Failed to refresh data.',
      )
    } finally {
      setRefreshLoading(false)
    }
  }

  // AUTO REFRESH: keep the command center synchronized with the backend.
  useEffect(() => {
    if (!token) return undefined

    let cancelled = false

    const syncData = async () => {
      try {
        await loadData(token, selectedLocation)
      } catch (error) {
        if (!cancelled) {
          console.error('Automatic data refresh error:', error)
        }
      }
    }

    const intervalId = window.setInterval(syncData, 15000)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [token, selectedLocation])

  async function login(usernameValue, passwordValue) {
    try {
      if (!usernameValue || !passwordValue) {
        throw new Error('Please enter username and password.')
      }

      const response = await fetch(
        `${API_BASE_URL}/api/auth/login`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            username: usernameValue,
            password: passwordValue,
          }),
        },
      )

      const data = await response.json()

      if (!response.ok || !data?.data?.access_token) {
        throw new Error(
          data?.detail ||
            data?.message ||
            'Invalid username or password.',
        )
      }

      const accessToken = data.data.access_token

      setToken(accessToken)
      await loadData(accessToken, 'Tawang')
    } catch (error) {
      console.error('Login error:', error)
      window.alert(error.message)
    }
  }

  // DEMO GPS SIMULATION ----------------------------------------------------
  // The backend already exposes PATCH /api/vehicles/{vehicle_id}/gps. We use
  // it for a controlled demo movement so the map, telemetry card and database
  // all move together without pretending that a physical GPS device exists.
  useEffect(() => {
    if (!simulationVehicleId && liveVehicles.length > 0) {
      setSimulationVehicleId(liveVehicles[0]?.vehicle_id || '')
    }

    if (
      simulationVehicleId &&
      !liveVehicles.some((item) => item?.vehicle_id === simulationVehicleId)
    ) {
      setSimulationVehicleId(liveVehicles[0]?.vehicle_id || '')
    }
  }, [liveVehicles, simulationVehicleId])

  function stopSimulation(message = '') {
    if (simulationTimerRef.current) {
      window.clearInterval(simulationTimerRef.current)
      simulationTimerRef.current = null
    }
    simulationRequestRef.current = false
    setSimulationRunning(false)
    if (message) setSimulationMessage(message)
  }

  function nearestNetworkLocation(latitude, longitude) {
    let nearest = null
    let bestDistance = Number.POSITIVE_INFINITY

    locations.forEach((item) => {
      const itemLat = Number(item?.latitude ?? item?.lat)
      const itemLon = Number(item?.longitude ?? item?.lon ?? item?.lng)
      if (!Number.isFinite(itemLat) || !Number.isFinite(itemLon)) return

      const distance = Math.hypot(itemLat - latitude, itemLon - longitude)
      if (distance < bestDistance) {
        bestDistance = distance
        nearest = item
      }
    })

    return nearest
  }

  async function pushSimulatedGps(vehicle, latitude, longitude, progress) {
    if (!token || !vehicle?.vehicle_id || simulationRequestRef.current) return

    simulationRequestRef.current = true
    try {
      const nearest = nearestNetworkLocation(latitude, longitude)
      const locationName =
        nearest?.location_name ||
        nearest?.name ||
        nearest?.location ||
        nearest?.city ||
        vehicle.current_location ||
        'Route simulation'

      const response = await fetch(
        `${API_BASE_URL}/api/vehicles/${encodeURIComponent(vehicle.vehicle_id)}/gps`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            current_location: locationName,
            latitude,
            longitude,
            current_road_id: vehicle.current_road_id || null,
            speed: simulationSpeed,
          }),
        },
      )

      const data = await response.json().catch(() => null)
      if (!response.ok || !data?.success) {
        throw new Error(
          data?.detail || data?.message || `GPS update failed (${response.status})`,
        )
      }

      const updated = data.data || {}
      setVehicles((current) =>
        current.map((item) =>
          item?.vehicle_id === vehicle.vehicle_id
            ? {
                ...item,
                ...updated,
                latitude,
                longitude,
                current_location: updated.current_location || locationName,
                speed: simulationSpeed,
                last_gps_update: updated.last_gps_update || new Date().toISOString(),
              }
            : item,
        ),
      )
      setSimulationProgress(Math.max(0, Math.min(100, progress)))
      setSimulationMessage('GPS telemetry synced to backend')
      setSimulationError('')
    } catch (error) {
      console.error('GPS simulation error:', error)
      setSimulationError(error?.message || 'GPS simulation update failed.')
      stopSimulation()
    } finally {
      simulationRequestRef.current = false
    }
  }

  function startSimulation() {
    const vehicle = liveVehicles.find(
      (item) => item?.vehicle_id === simulationVehicleId,
    )

    if (!vehicle) {
      setSimulationError('Select a live vehicle first.')
      return
    }

    if (!gisRoute?.latLngs || gisRoute.latLngs.length < 2) {
      setSimulationError('Plan a GIS route first, then start GPS simulation.')
      return
    }

    if (simulationTimerRef.current) return

    setSimulationError('')
    setSimulationMessage('Starting controlled GPS simulation…')
    setSimulationRunning(true)

    const path = gisRoute.latLngs
    const startIndex = Math.max(
      0,
      Math.min(
        path.length - 1,
        Math.round((simulationProgress / 100) * (path.length - 1)),
      ),
    )
    simulationIndexRef.current = startIndex

    const tick = async () => {
      const currentVehicle = vehicles.find(
        (item) => item?.vehicle_id === simulationVehicleId,
      ) || vehicle
      const index = simulationIndexRef.current
      const point = path[index]
      if (!point) {
        stopSimulation('GPS simulation completed')
        return
      }

      const progress = (index / (path.length - 1)) * 100
      await pushSimulatedGps(
        currentVehicle,
        Number(point[0]),
        Number(point[1]),
        progress,
      )

      if (index >= path.length - 1) {
        stopSimulation('GPS simulation completed')
        setSimulationProgress(100)
        return
      }

      // Faster demo speed = larger step along the route while keeping the
      // backend updates smooth enough to observe on the map.
      const step = Math.max(1, Math.round(simulationSpeed / 15))
      simulationIndexRef.current = Math.min(path.length - 1, index + step)
    }

    tick()
    simulationTimerRef.current = window.setInterval(tick, 2500)
  }

  function resetSimulation() {
    stopSimulation('Simulation reset')
    setSimulationProgress(0)
    setSimulationError('')

    const vehicle = liveVehicles.find(
      (item) => item?.vehicle_id === simulationVehicleId,
    )
    const firstPoint = gisRoute?.latLngs?.[0]
    if (vehicle && firstPoint) {
      pushSimulatedGps(vehicle, Number(firstPoint[0]), Number(firstPoint[1]), 0)
    }
  }

  useEffect(() => {
    return () => {
      if (simulationTimerRef.current) {
        window.clearInterval(simulationTimerRef.current)
      }
    }
  }, [])

  // ROUTE PLANNER
  async function planRoute() {
    if (!token) {
      setRouteError('Connecting to backend...')
      return
    }

    if (!from.trim() || !to.trim()) {
      setRouteError('Select both route locations.')
      return
    }

    if (from.trim() === to.trim()) {
      setRouteError('Start and destination must be different.')
      return
    }

    setRouteLoading(true)
    setRouteError('')
    setRoute(null)
    setGisRoute(null)
    setGisRouteError('')

    // The UI displays friendly location names, while the route service may
    // identify the same place by a backend node/location ID. Try the backend
    // value first and, when the API reports a location lookup failure, retry
    // once with the human-readable location name. This keeps the UI simple
    // without hardcoding a Tawang/Itanagar mapping.
    const fromOption = routeLocationOptions.find(
      (option) => option.value === from.trim(),
    )
    const toOption = routeLocationOptions.find(
      (option) => option.value === to.trim(),
    )

    const fromCandidates = [
      from.trim(),
      fromOption?.label?.trim(),
    ].filter(Boolean).filter(
      (value, index, values) => values.indexOf(value) === index,
    )

    const toCandidates = [
      to.trim(),
      toOption?.label?.trim(),
    ].filter(Boolean).filter(
      (value, index, values) => values.indexOf(value) === index,
    )

    const locationLookupFailure = (message) => {
      const text = String(message || '').toLowerCase()
      return (
        text.includes('not found') ||
        text.includes('unknown location') ||
        text.includes('location not') ||
        text.includes('node not') ||
        text.includes('unknown node') ||
        text.includes('invalid location')
      )
    }

    try {
      let lastError = 'Route planning failed.'

      for (const startCandidate of fromCandidates) {
        for (const destinationCandidate of toCandidates) {
          if (startCandidate === destinationCandidate) continue

          try {
            const response = await fetch(
              `${API_BASE_URL}/api/routes/plan`,
              {
                method: 'POST',
                headers: {
                  Authorization: `Bearer ${token}`,
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  trip_id: `DEMO-${Date.now()}`,
                  start_location: startCandidate,
                  destination_location: destinationCandidate,
                }),
              },
            )

            let data = null
            try {
              data = await response.json()
            } catch {
              data = null
            }

            if (response.ok && data?.success) {
              setRoute(data)
              await fetchGISRoadRoute(data)
              return
            }

            lastError =
              data?.detail ||
              data?.message ||
              `Route planning failed (HTTP ${response.status}).`

            // If this is a genuine location lookup mismatch, try the next
            // representation of the same location. Other backend errors are
            // surfaced immediately instead of being hidden by retries.
            if (!locationLookupFailure(lastError)) {
              throw new Error(lastError)
            }
          } catch (candidateError) {
            lastError = candidateError.message || 'Route planning failed.'

            if (!locationLookupFailure(lastError)) {
              throw candidateError
            }
          }
        }
      }

      throw new Error(
        `The route service could not resolve the selected locations. ${lastError}`,
      )
    } catch (error) {
      console.error('Route error:', error)
      setRouteError(error.message)
    } finally {
      setRouteLoading(false)
    }
  }

  // AUTOMATIC INCIDENT -> REROUTE
  // When a new/changed active incident appears, use the existing backend route
  // planner so its active blocked-road list is included in the ML decision.
  useEffect(() => {
    const activeKey = activeIncidents
      .map((item) => `${item?.incident_id || ''}:${item?.status || ''}:${item?.road_id || ''}:${item?.severity || ''}`)
      .sort()
      .join('|')

    if (!token || !activeKey || !from || !to || from === to) {
      if (!activeKey) {
        autoIncidentRouteRef.current = ''
        setIncidentRouteStatus('')
      }
      return
    }

    if (autoIncidentRouteRef.current === activeKey) return
    autoIncidentRouteRef.current = activeKey

    const timer = window.setTimeout(async () => {
      setIncidentRouteStatus(
        `${activeIncidents.length} active incident${activeIncidents.length === 1 ? '' : 's'} detected. Recalculating the safest route…`,
      )
      await planRoute()
      setIncidentRouteStatus(
        `Route recalculated using ${activeBlockedRoads.length || activeIncidents.filter((item) => item?.road_id).length} active blocked road${(activeBlockedRoads.length || activeIncidents.filter((item) => item?.road_id).length) === 1 ? '' : 's'}.`,
      )
    }, 650)

    return () => window.clearTimeout(timer)
  }, [token, activeIncidents, from, to])

  // INCIDENT FORM HANDLER
  function handleIncidentChange(event) {
    const { name, value } = event.target

    setIncidentForm((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  // REPORT INCIDENT
  async function reportIncident(event) {
    event.preventDefault()

    if (!token) {
      setIncidentError('Connecting to backend...')
      return
    }

    if (
      !incidentForm.incident_type.trim() ||
      !incidentForm.location.trim()
    ) {
      setIncidentError(
        'Incident type and location are required.',
      )
      return
    }

    setIncidentLoading(true)
    setIncidentMessage('')
    setIncidentError('')

    try {
      const payload = {
        incident_type: incidentForm.incident_type.trim(),
        severity: incidentForm.severity,
        location: incidentForm.location.trim(),
        road_id: incidentForm.road_id.trim() || null,
        description:
          incidentForm.description.trim() || null,
        latitude:
          incidentForm.latitude.trim() !== ''
            ? Number(incidentForm.latitude)
            : null,
        longitude:
          incidentForm.longitude.trim() !== ''
            ? Number(incidentForm.longitude)
            : null,
      }

      const response = await fetch(
        `${API_BASE_URL}/api/incidents`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        },
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data?.detail || 'Failed to report incident',
        )
      }

      if (!data.success) {
        throw new Error(
          data?.message || 'Failed to report incident',
        )
      }

      setIncidentMessage(
        'Incident reported successfully.',
      )

      setIncidentForm({
        incident_type: 'ROAD BLOCKAGE',
        severity: 'HIGH',
        location: '',
        road_id: '',
        description: '',
        latitude: '',
        longitude: '',
      })

      // Reload dashboard + incidents
      await loadData(token, selectedLocation)

      // Close form after successful submission
      setTimeout(() => {
        setShowIncidentForm(false)
        setIncidentMessage('')
      }, 1200)
    } catch (error) {
      console.error('Incident error:', error)
      setIncidentError(error.message)
    } finally {
      setIncidentLoading(false)
    }
  }


  // RESOLVE INCIDENT
  async function resolveIncident(incidentId) {
    if (!token || !incidentId) {
      return
    }

    const confirmed = window.confirm(
      'Are you sure you want to resolve this incident?',
    )

    if (!confirmed) {
      return
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/incidents/${incidentId}/resolve`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        },
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data?.detail || 'Failed to resolve incident',
        )
      }

      if (!data.success) {
        throw new Error(
          data?.message || 'Failed to resolve incident',
        )
      }

      await loadData(token, selectedLocation)
    } catch (error) {
      console.error('Resolve incident error:', error)
      window.alert(error.message)
    }
  }

  // VEHICLE FORM HANDLER
  function handleVehicleChange(event) {
    const { name, value } = event.target

    setVehicleForm((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  // REGISTER VEHICLE
  async function registerVehicle(event) {
    event.preventDefault()

    if (!token) {
      setVehicleError('Connecting to backend...')
      return
    }

    if (
      !vehicleForm.vehicle_type.trim() ||
      !vehicleForm.current_location.trim()
    ) {
      setVehicleError(
        'Vehicle type and current location are required.',
      )
      return
    }

    setVehicleLoading(true)
    setVehicleMessage('')
    setVehicleError('')

    try {
      const payload = {
        vehicle_type: vehicleForm.vehicle_type.trim(),
        driver_name: vehicleForm.driver_name.trim() || null,
        cargo_type: vehicleForm.cargo_type.trim() || null,
        current_location:
          vehicleForm.current_location.trim() || null,
        latitude:
          vehicleForm.latitude.trim() !== ''
            ? Number(vehicleForm.latitude)
            : null,
        longitude:
          vehicleForm.longitude.trim() !== ''
            ? Number(vehicleForm.longitude)
            : null,
        current_road_id:
          vehicleForm.current_road_id.trim() || null,
        speed:
          vehicleForm.speed.trim() !== ''
            ? Number(vehicleForm.speed)
            : null,
      }

      const response = await fetch(
        `${API_BASE_URL}/api/vehicles`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        },
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data?.detail || 'Failed to register vehicle',
        )
      }

      if (!data.success) {
        throw new Error(
          data?.message || 'Failed to register vehicle',
        )
      }

      setVehicleMessage(
        `Vehicle ${data?.data?.vehicle_id || ''} registered successfully.`,
      )

      setVehicleForm({
        vehicle_type: 'RESCUE TRUCK',
        driver_name: '',
        cargo_type: '',
        current_location: '',
        latitude: '',
        longitude: '',
        current_road_id: '',
        speed: '',
      })

      await loadData(token, selectedLocation)

      setTimeout(() => {
        setShowVehicleForm(false)
        setVehicleMessage('')
      }, 1200)
    } catch (error) {
      console.error('Vehicle registration error:', error)
      setVehicleError(error.message)
    } finally {
      setVehicleLoading(false)
    }
  }

  const recommended = route?.data?.recommended_route
  const decision = route?.ai_decision

  const risk = recommended
    ? Math.round(
        recommended.risk_probability * 100,
      )
    : null

  const activeBlockedRoads =
    route?.active_blocked_roads || []

  const weatherRisk =
    weather?.risk?.score != null
      ? Math.round(weather.risk.score * 100)
      : null

  // DYNAMIC MAP DATA
  const validMapLocations = locations.filter((item) =>
    Number.isFinite(Number(item.latitude)) &&
    Number.isFinite(Number(item.longitude)),
  )

  const validMapVehicles = vehicles.filter((item) =>
    Number.isFinite(Number(item.latitude)) &&
    Number.isFinite(Number(item.longitude)),
  )

  const validMapIncidents = incidents.filter((item) =>
    Number.isFinite(Number(item.latitude)) &&
    Number.isFinite(Number(item.longitude)),
  )

  const allMapPoints = [
    ...validMapLocations,
    ...validMapVehicles,
    ...validMapIncidents,
  ]

  const mapLatitudes = allMapPoints.map((item) => Number(item.latitude))
  const mapLongitudes = allMapPoints.map((item) => Number(item.longitude))

  const minLat = mapLatitudes.length ? Math.min(...mapLatitudes) : 8
  const maxLat = mapLatitudes.length ? Math.max(...mapLatitudes) : 30
  const minLon = mapLongitudes.length ? Math.min(...mapLongitudes) : 72
  const maxLon = mapLongitudes.length ? Math.max(...mapLongitudes) : 98
  const latRange = Math.max(maxLat - minLat, 0.5)
  const lonRange = Math.max(maxLon - minLon, 0.5)

  function getMapPosition(latitude, longitude) {
    const x = 8 + ((Number(longitude) - minLon) / lonRange) * 84
    const y = 90 - ((Number(latitude) - minLat) / latRange) * 78

    return {
      left: `${Math.min(92, Math.max(8, x))}%`,
      top: `${Math.min(90, Math.max(10, y))}%`,
    }
  }

  // Cluster nearby locations so all 100+ backend points do not overlap.
  const locationClusters = validMapLocations.reduce((clusters, item) => {
    const position = getMapPosition(item.latitude, item.longitude)
    const x = parseFloat(position.left)
    const y = parseFloat(position.top)

    let cluster = clusters.find(
      (entry) => Math.abs(entry.x - x) < 5 && Math.abs(entry.y - y) < 5,
    )

    if (!cluster) {
      cluster = { x, y, items: [] }
      clusters.push(cluster)
    }

    cluster.items.push(item)

    cluster.x = cluster.items.reduce(
      (sum, point) =>
        sum + parseFloat(getMapPosition(point.latitude, point.longitude).left),
      0,
    ) / cluster.items.length

    cluster.y = cluster.items.reduce(
      (sum, point) =>
        sum + parseFloat(getMapPosition(point.latitude, point.longitude).top),
      0,
    ) / cluster.items.length

    return clusters
  }, [])

  // ROUTE MAP ENDPOINTS
  function findLocationCoordinates(locationValue) {
    const target = String(locationValue || '').trim().toLowerCase()
    if (!target) return null

    const match = locations.find((item) => {
      const candidates = [
        item?.location_name,
        item?.name,
        item?.location,
        item?.city,
        item?.location_id,
        item?.node_id,
        item?.id,
      ]
        .filter((value) => value !== undefined && value !== null)
        .map((value) => String(value).trim().toLowerCase())

      return candidates.includes(target)
    })

    if (!match) return null

    const latitude = Number(match?.latitude ?? match?.lat)
    const longitude = Number(
      match?.longitude ?? match?.lon ?? match?.lng,
    )

    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      return null
    }

    return [latitude, longitude]
  }

  async function fetchGISRoadRoute(routeData) {
    const network = routeData?.route_network
    const recommendedRoute = routeData?.data?.recommended_route

    const coordinates = Array.isArray(network?.coordinates)
      ? network.coordinates
          .map((point) => [Number(point?.[0]), Number(point?.[1])])
          .filter(([latitude, longitude]) =>
            Number.isFinite(latitude) && Number.isFinite(longitude),
          )
      : []

    if (coordinates.length < 2) {
      setGisRoute(null)
      setGisRouteError(
        'The backend did not return enough network geometry for the ML-selected route.',
      )
      return
    }

    setGisRouteLoading(true)
    setGisRouteError('')

    try {
      // IMPORTANT: do not calculate a second independent shortest route here.
      // The backend has already selected the route using the project's ML model.
      // We visualize that exact ordered synthetic road-network path on Leaflet.
      setGisRoute({
        latLngs: coordinates,
        distanceKm: Number(recommendedRoute?.distance_km || 0),
        durationMinutes:
          Number(recommendedRoute?.estimated_travel_time_hours || 0) * 60,
        roadIds: Array.isArray(network?.road_ids)
          ? network.road_ids
          : Array.isArray(recommendedRoute?.road_ids)
            ? recommendedRoute.road_ids
            : [],
        geometrySource:
          network?.geometry_source || 'NER-RESQ synthetic road network',
      })
    } catch (error) {
      console.error('ML network route visualization error:', error)
      setGisRoute(null)
      setGisRouteError(
        error?.message || 'ML route geometry is unavailable.',
      )
    } finally {
      setGisRouteLoading(false)
    }
  }

  // REAL GEOGRAPHIC MAP
  useEffect(() => {
    if (!token || !mapRef.current) return

    if (!leafletMapRef.current) {
      const map = L.map(mapRef.current, {
        zoomControl: true,
        scrollWheelZoom: true,
      }).setView([27.5, 94.5], 6.2)

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map)

      leafletMapRef.current = map
      leafletLayerRef.current = L.layerGroup().addTo(map)
    }

    const map = leafletMapRef.current
    const layer = leafletLayerRef.current
    layer.clearLayers()

    const points = []

    const getCoords = (item) => {
      const latitude = Number(item?.latitude ?? item?.lat)
      const longitude = Number(
        item?.longitude ?? item?.lon ?? item?.lng,
      )

      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        return null
      }

      return [latitude, longitude]
    }

    // Network locations: small blue dots keep the 100+ points readable.
    locations.forEach((item, index) => {
      const coords = getCoords(item)
      if (!coords) return
      points.push(coords)

      const name =
        item?.location_name ||
        item?.name ||
        item?.location ||
        `Network location ${index + 1}`

      L.circleMarker(coords, {
        radius: 5,
        weight: 2,
        opacity: 0.95,
        fillOpacity: 0.9,
        className: 'map-location-marker',
      })
        .bindPopup(`
          <div class="map-popup">
            <strong>${name}</strong>
            <span>NETWORK LOCATION</span>
            <small>${coords[0].toFixed(4)}, ${coords[1].toFixed(4)}</small>
          </div>
        `)
        .addTo(layer)
    })

    // Vehicles: green markers.
    vehicles.forEach((item, index) => {
      const coords = getCoords(item)
      if (!coords) return
      points.push(coords)

      const icon = L.divIcon({
        className: 'leaflet-vehicle-icon',
        html: '<span>V</span>',
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      })

      L.marker(coords, { icon })
        .bindPopup(`
          <div class="map-popup">
            <strong>${item?.vehicle_id || `Vehicle ${index + 1}`}</strong>
            <span>ACTIVE VEHICLE</span>
            <small>${item?.current_location || 'Location unavailable'}</small>
            <small>Road: ${item?.current_road_id || 'N/A'}</small>
            <small>Status: ${item?.status || 'UNKNOWN'}</small>
            <small>Speed: ${item?.speed != null ? `${Number(item.speed)} km/h` : 'N/A'}</small>
            <small>GPS: ${item?.last_gps_update ? new Date(item.last_gps_update).toLocaleString() : 'N/A'}</small>
          </div>
        `)
        .addTo(layer)
    })

    // Incidents: red alert markers.
    activeIncidents.forEach((item) => {
      const coords = getCoords(item)
      if (!coords) return
      points.push(coords)

      const icon = L.divIcon({
        className: 'leaflet-incident-icon',
        html: '<span>!</span>',
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      })

      L.marker(coords, { icon })
        .bindPopup(`
          <div class="map-popup">
            <strong>${item?.incident_type || 'INCIDENT'}</strong>
            <span>${item?.severity || 'UNKNOWN'} · ${item?.status || 'ACTIVE'}</span>
            <small>${item?.location || 'Location unavailable'}</small>
            <small>Road: ${item?.road_id || 'N/A'}</small>
          </div>
        `)
        .addTo(layer)
    })

    // ML route visualization: backend supplies the exact ordered road-network path
    // selected by the route engine; Leaflet renders that path geographically.
    if (route?.success) {
      const startCoords = findLocationCoordinates(route.start_location)
      const destinationCoords = findLocationCoordinates(route.destination_location)

      if (startCoords && destinationCoords) {
        points.push(startCoords, destinationCoords)

        if (gisRoute?.latLngs?.length >= 2) {
          L.polyline(gisRoute.latLngs, {
            weight: 6,
            opacity: 0.95,
            className: 'ai-road-route',
          })
            .bindPopup(`
              <div class="map-popup">
                <strong>ML NETWORK ROUTE</strong>
                <span>${route.start_location} → ${route.destination_location}</span>
                <small>ML predicted risk: ${risk != null ? `${risk}%` : 'N/A'}</small>
                <small>Selected roads: ${(gisRoute.roadIds || recommended?.road_ids || []).join(', ') || 'N/A'}</small>
                <small>ML route distance: ${gisRoute.distanceKm.toFixed(1)} km</small>
              </div>
            `)
            .addTo(layer)
          gisRoute.latLngs.forEach((coords) => points.push(coords))
        } else {
          L.polyline([startCoords, destinationCoords], {
            weight: 4,
            opacity: 0.55,
            dashArray: '10 8',
            className: 'ai-route-corridor',
          })
            .bindPopup(`
              <div class="map-popup">
                <strong>ML ROUTE CORRIDOR</strong>
                <span>${route.start_location} → ${route.destination_location}</span>
                <small>ML network geometry unavailable</small>
                <small>Predicted risk: ${risk != null ? `${risk}%` : 'N/A'}</small>
              </div>
            `)
            .addTo(layer)
        }

        const startIcon = L.divIcon({
          className: '',
          html: '<div style="width:28px;height:28px;border-radius:50%;background:#0ea5e9;color:#fff;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;">S</div>',
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        })
        const destinationIcon = L.divIcon({
          className: '',
          html: '<div style="width:28px;height:28px;border-radius:50%;background:#f97316;color:#fff;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;">D</div>',
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        })

        L.marker(startCoords, { icon: startIcon })
          .bindPopup(`<div class="map-popup"><strong>START</strong><span>${route.start_location}</span></div>`)
          .addTo(layer)
        L.marker(destinationCoords, { icon: destinationIcon })
          .bindPopup(`<div class="map-popup"><strong>DESTINATION</strong><span>${route.destination_location}</span></div>`)
          .addTo(layer)
      }
    }

    if (points.length > 0) {
      const bounds = L.latLngBounds(points)
      map.fitBounds(bounds, { padding: [35, 35], maxZoom: 9 })
    }

    window.setTimeout(() => map.invalidateSize(), 100)
  }, [token, locations, vehicles, incidents, route, risk, recommended, gisRoute])

  useEffect(() => {
    return () => {
      if (leafletMapRef.current) {
        leafletMapRef.current.remove()
        leafletMapRef.current = null
        leafletLayerRef.current = null
      }
    }
  }, [])

  return (
    !token ? (
      <div className="login-page">
        <div className="login-card">
          <div className="login-logo">NER-RESq</div>

          <h1>Command Center Login</h1>
          <p>
            Sign in to access the emergency logistics dashboard.
          </p>

          <form
            onSubmit={(event) => {
              event.preventDefault()
              login(username, password)
            }}
          >
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Enter username"
              autoComplete="username"
            />

            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password"
              autoComplete="current-password"
            />

            <button type="submit">SIGN IN</button>
          </form>

          <div className="login-demo">
            Demo operator account: <strong>operator1</strong>
          </div>
        </div>
      </div>
    ) : (
      <div className="app">

      <style>{`
        .vehicle-live-card { overflow: hidden; }
        .vehicle-live-header { align-items: flex-start; }
        .vehicle-live-subtitle { margin: 6px 0 0; font-size: 12px; opacity: .62; }
        .vehicle-live-indicator { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
        .live-pulse { width: 9px; height: 9px; border-radius: 50%; background: #16a34a; box-shadow: 0 0 0 5px rgba(22,163,74,.10); animation: vehiclePulse 1.8s infinite; }
        @keyframes vehiclePulse { 0%,100% { transform: scale(1); opacity: 1; } 50% { transform: scale(.78); opacity: .62; } }
        .vehicle-sim-panel { margin-top: 18px; padding: 20px; border: 1px solid rgba(148,163,184,.20); border-radius: 16px; background: linear-gradient(135deg, rgba(15,23,42,.045), rgba(14,165,233,.045)); }
        .vehicle-sim-heading { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
        .vehicle-sim-kicker { display: block; font-size: 10px; letter-spacing: .18em; font-weight: 800; opacity: .58; }
        .vehicle-sim-heading h3 { margin: 6px 0 5px; font-size: 18px; }
        .vehicle-sim-heading p { margin: 0; max-width: 720px; font-size: 12px; line-height: 1.55; opacity: .66; }
        .sim-status-pill, .vehicle-status-pill { display: inline-flex; align-items: center; gap: 7px; border: 1px solid rgba(148,163,184,.22); border-radius: 999px; padding: 7px 10px; font-size: 10px; font-weight: 800; letter-spacing: .08em; white-space: nowrap; }
        .sim-status-pill span, .vehicle-status-pill i { width: 7px; height: 7px; border-radius: 50%; background: #94a3b8; }
        .sim-status-pill.is-running { border-color: rgba(14,165,233,.30); background: rgba(14,165,233,.08); color: #0369a1; }
        .sim-status-pill.is-running span { background: #0ea5e9; box-shadow: 0 0 0 4px rgba(14,165,233,.10); }
        .vehicle-sim-controls { display: grid; grid-template-columns: minmax(250px,1.2fr) minmax(220px,.9fr) auto; gap: 14px; margin-top: 18px; align-items: end; }
        .vehicle-sim-select, .vehicle-speed-control { display: flex; flex-direction: column; gap: 7px; }
        .vehicle-sim-select > span, .vehicle-speed-control span { font-size: 9px; font-weight: 800; letter-spacing: .15em; opacity: .56; }
        .vehicle-sim-select select { width: 100%; min-height: 42px; border: 1px solid rgba(148,163,184,.25); border-radius: 10px; background: rgba(255,255,255,.72); padding: 0 12px; font: inherit; color: inherit; outline: none; }
        .vehicle-speed-control > div { display:flex; justify-content:space-between; align-items:center; }
        .vehicle-speed-control strong { font-size: 12px; }
        .vehicle-speed-control input { width: 100%; accent-color: #0ea5e9; }
        .vehicle-sim-actions { display:flex; gap: 8px; }
        .vehicle-sim-actions button { min-height: 42px; border-radius: 10px; padding: 0 14px; border: 1px solid rgba(148,163,184,.22); font-size: 10px; font-weight: 800; letter-spacing: .08em; cursor:pointer; }
        .vehicle-sim-actions button:disabled { opacity:.42; cursor:not-allowed; }
        .sim-primary-button { background:#0f172a; color:#fff; }
        .sim-stop-button { background:#dc2626; color:#fff; border-color:#dc2626 !important; }
        .sim-secondary-button { background:rgba(255,255,255,.72); color:inherit; }
        .vehicle-progress-wrap { margin-top: 18px; }
        .vehicle-progress-meta { display:flex; justify-content:space-between; gap:12px; font-size:11px; opacity:.68; }
        .vehicle-progress-meta strong { opacity:1; }
        .vehicle-progress-track { height: 8px; margin-top: 8px; background: rgba(148,163,184,.17); border-radius:999px; overflow:hidden; }
        .vehicle-progress-fill { height:100%; border-radius:inherit; background: linear-gradient(90deg,#0ea5e9,#2563eb); transition: width .35s ease; }
        .vehicle-progress-fill.is-running { animation: progressGlow 1.5s ease-in-out infinite alternate; }
        @keyframes progressGlow { from { filter: brightness(.96); } to { filter: brightness(1.18); } }
        .vehicle-sim-feedback { display:flex; justify-content:space-between; gap:12px; margin-top:8px; font-size:10px; opacity:.62; }
        .vehicle-sim-feedback b { color:#dc2626; font-weight:700; }
        .vehicle-live-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:14px; margin-top:16px; }
        .vehicle-live-item { border:1px solid rgba(148,163,184,.20); border-radius:14px; padding:16px; background:rgba(255,255,255,.46); transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
        .vehicle-live-item.is-simulating { border-color:rgba(14,165,233,.45); box-shadow:0 10px 28px rgba(14,165,233,.10); }
        .vehicle-live-item-top { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
        .vehicle-live-item-top > div { display:flex; flex-direction:column; gap:5px; }
        .vehicle-type-tag { font-size:9px; font-weight:800; letter-spacing:.13em; opacity:.48; }
        .vehicle-live-item-top strong { font-size:15px; }
        .vehicle-status-pill.simulating { background:rgba(14,165,233,.08); border-color:rgba(14,165,233,.28); color:#0369a1; }
        .vehicle-status-pill.simulating i { background:#0ea5e9; }
        .vehicle-telemetry-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:16px; }
        .vehicle-telemetry-grid div { padding:10px; border-radius:10px; background:rgba(148,163,184,.075); }
        .vehicle-telemetry-grid span { display:block; font-size:8px; font-weight:800; letter-spacing:.13em; opacity:.50; }
        .vehicle-telemetry-grid strong { display:block; margin-top:4px; font-size:12px; font-weight:700; word-break:break-word; }
        .vehicle-live-footer { display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; margin-top:14px; padding-top:12px; border-top:1px solid rgba(148,163,184,.14); font-size:9px; letter-spacing:.04em; opacity:.58; }
        .vehicle-live-footer span:first-child { display:flex; align-items:center; gap:6px; }
        .gps-dot { width:6px; height:6px; border-radius:50%; background:#16a34a; display:inline-block; }
        .vehicle-empty-state { display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:6px; min-height:150px; opacity:.72; }
        .vehicle-empty-icon { font-size:30px; opacity:.45; }
        @media (max-width: 900px) { .vehicle-sim-controls { grid-template-columns:1fr; } .vehicle-sim-actions { width:100%; } .vehicle-sim-actions button { flex:1; } .vehicle-sim-heading { flex-direction:column; } }
      `}</style>

      {/* HEADER */}
      <header className="header">
        <div className="logo-area">
          <div className="logo">NR</div>

          <div>
            <div className="logo-title">NER-RESQ</div>

            <div className="logo-subtitle">
              SMART LOGISTICS COMMAND CENTER
            </div>
          </div>
        </div>

        <div className="system">
          <span className="green-dot"></span>

          <div>
            <b>SYSTEM OPERATIONAL</b>
            <small>LIVE CONTROL NETWORK</small>
          </div>

          <div className="sync">
            <small>LAST SYNC</small>
            <b>
              {lastSync ? lastSync.toLocaleTimeString() : 'SYNCING...'}
            </b>
          </div>
        </div>
      </header>

      {/* CONTENT */}
      <main className="container">

        {/* TITLE */}
        <section className="hero">
          <div>
            <span className="label">
              NATIONAL EMERGENCY RESPONSE
            </span>

            <h1>Operations Command</h1>

            <p>
              Monitor fleet activity, road risk,
              incidents and AI-powered logistics
              decisions.
            </p>
          </div>

          <div className="live">
            <span className="green-dot"></span>
            LIVE OPERATIONS
          </div>
        </section>

        {/* STATS */}
        <section className="stats">

          <div className="stat">
            <span>LOCATIONS</span>

            <strong>
              {locations.length || '—'}
            </strong>

            <small>Network locations</small>
          </div>

          <div className="stat">
            <span>AVAILABLE</span>

            <strong>
              {dashboard?.vehicles?.available ?? '—'}
            </strong>

            <small>Vehicles available</small>
          </div>

          <div className="stat">
            <span>BLOCKED</span>

            <strong className="red">
              {dashboard?.incidents?.active ?? '—'}
            </strong>

            <small>Active incidents</small>
          </div>

          <div className="stat">
            <span>ACTIVE VEHICLES</span>

            <strong>
              {activeVehicleCount}
            </strong>

            <small>Fleet connected</small>
          </div>

        </section>

        {/* MAP + INCIDENTS */}
        <section className="two-column">

          {/* MAP */}
          <div className="card">

            <div className="card-header">
              <div>
                <span className="label">
                  LIVE OPERATIONS MAP
                </span>

                <h2>Logistics Network</h2>
              </div>

              <span className="live-text">
                <span className="green-dot"></span>
                LIVE
              </span>
            </div>

            <div className="leaflet-map-shell">
              <div ref={mapRef} className="leaflet-map" />

              <div className="map-count leaflet-count">
                <span>NETWORK LOCATIONS</span>
                <strong>{locations.length}</strong>
              </div>

              <div className="leaflet-legend">
                <span><i className="legend-dot location-dot"></i> LOCATION</span>
                <span><i className="legend-dot vehicle-dot"></i> VEHICLE</span>
                <span><i className="legend-dot incident-dot"></i> INCIDENT</span>
              </div>
            </div>
          </div>

          {/* INCIDENTS */}
          <div className="card">

            <div className="card-header">

              <div>
                <span className="label">
                  ALERT CENTER
                </span>

                <h2>Live Incidents</h2>
              </div>

              <span className="count">
                {activeIncidents.length}
              </span>

            </div>

            <div className="incidents">

              {activeIncidents.length === 0 ? (

                <div className="empty">
                  No active incidents.
                </div>

              ) : (

                activeIncidents.map((item) => (

                  <div
                    className="incident-item"
                    key={item.incident_id}
                  >

                    <span
                      className={`severity ${
                        String(
                          item.severity || '',
                        ).toLowerCase()
                      }`}
                    ></span>

                    <div>

                      <div className="incident-title">

                        <b>
                          {item.incident_type}
                        </b>

                        <small>
                          {item.created_at
                            ? new Date(
                                item.created_at,
                              ).toLocaleTimeString()
                            : 'LIVE'}
                        </small>

                      </div>

                      <strong className="location">
                        {item.location}
                      </strong>

                      <small>
                        ROAD {item.road_id || 'N/A'}
                      </small>

                      {item.description && (
                        <p>
                          {item.description}
                        </p>
                      )}

                      {item.status !== 'RESOLVED' && (
                        <button
                          className="resolve-button"
                          onClick={() =>
                            resolveIncident(item.incident_id)
                          }
                        >
                          RESOLVE
                        </button>
                      )}

                    </div>

                  </div>

                ))

              )}

            </div>
          </div>

        </section>

        {/* ROAD STATUS */}
        <section className="card road-card">

          <div className="card-header">

            <div>
              <span className="label">
                NETWORK STATUS
              </span>

              <h2>Selected Road</h2>
            </div>

            <b>{selectedRoad}</b>

          </div>

          <div className="road-stats">

            <div>
              <span>STATUS</span>
              <strong className={roadStatusClass}>
                {roadStatus}
              </strong>
            </div>

            <div>
              <span>ACTIVE INCIDENT</span>
              <strong>
                {activeIncidents.length}
              </strong>
            </div>

            <div>
              <span>VEHICLES</span>
              <strong>
                {vehicles.length}
              </strong>
            </div>

            <div>
              <span>NETWORK</span>
              <strong>
                {locations.length > 0 ? 'MONITORED' : 'OFFLINE'}
              </strong>
            </div>

          </div>
        </section>

        {/* LIVE VEHICLE TRACKING */}
        <section className="card vehicle-live-card" style={{ marginTop: '18px' }}>

          <div className="card-header vehicle-live-header">
            <div>
              <span className="label">LIVE TELEMETRY</span>
              <h2>Vehicle Tracking</h2>
              <p className="vehicle-live-subtitle">
                Backend GPS feed · 15s sync · controlled demo movement
              </p>
            </div>
            <div className="vehicle-live-indicator">
              <span className="live-pulse"></span>
              <b>{liveVehicles.length} LIVE</b>
            </div>
          </div>

          <div className="vehicle-sim-panel">
            <div className="vehicle-sim-heading">
              <div>
                <span className="vehicle-sim-kicker">GPS DEMO CONTROL</span>
                <h3>Live Movement Simulator</h3>
                <p>
                  Move a real backend vehicle along the planned GIS route. Every
                  position is written through the vehicle GPS API.
                </p>
              </div>
              <div className={`sim-status-pill ${simulationRunning ? 'is-running' : ''}`}>
                <span></span>
                {simulationRunning ? 'SIMULATION ACTIVE' : 'STANDBY'}
              </div>
            </div>

            <div className="vehicle-sim-controls">
              <label className="vehicle-sim-select">
                <span>VEHICLE</span>
                <select
                  value={simulationVehicleId}
                  onChange={(event) => {
                    stopSimulation()
                    setSimulationVehicleId(event.target.value)
                    setSimulationProgress(0)
                  }}
                  disabled={simulationRunning || liveVehicles.length === 0}
                >
                  {liveVehicles.length === 0 ? (
                    <option value="">No live vehicles</option>
                  ) : (
                    liveVehicles.map((vehicle) => (
                      <option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>
                        {vehicle.vehicle_id} · {vehicle.current_location || 'Unknown'}
                      </option>
                    ))
                  )}
                </select>
              </label>

              <label className="vehicle-speed-control">
                <div>
                  <span>SIM SPEED</span>
                  <strong>{simulationSpeed} km/h</strong>
                </div>
                <input
                  type="range"
                  min="20"
                  max="80"
                  step="5"
                  value={simulationSpeed}
                  onChange={(event) => setSimulationSpeed(Number(event.target.value))}
                  disabled={simulationRunning}
                />
              </label>

              <div className="vehicle-sim-actions">
                {!simulationRunning ? (
                  <button
                    type="button"
                    className="sim-primary-button"
                    onClick={startSimulation}
                    disabled={!simulationVehicleId || !gisRoute?.latLngs?.length}
                  >
                    ▶ START MOVEMENT
                  </button>
                ) : (
                  <button
                    type="button"
                    className="sim-stop-button"
                    onClick={() => stopSimulation('Simulation paused')}
                  >
                    ■ PAUSE
                  </button>
                )}
                <button
                  type="button"
                  className="sim-secondary-button"
                  onClick={resetSimulation}
                  disabled={!simulationVehicleId || !gisRoute?.latLngs?.length}
                >
                  ↺ RESET
                </button>
              </div>
            </div>

            <div className="vehicle-progress-wrap">
              <div className="vehicle-progress-meta">
                <span>
                  {gisRoute?.latLngs?.length
                    ? `GIS route · ${gisRoute.distanceKm.toFixed(1)} km`
                    : 'Plan a GIS route to enable movement'}
                </span>
                <strong>{Math.round(simulationProgress)}%</strong>
              </div>
              <div className="vehicle-progress-track">
                <div
                  className={`vehicle-progress-fill ${simulationRunning ? 'is-running' : ''}`}
                  style={{ width: `${simulationProgress}%` }}
                ></div>
              </div>
              <div className="vehicle-sim-feedback">
                <span>{simulationMessage || 'Ready for controlled GPS simulation.'}</span>
                {simulationError && <b>{simulationError}</b>}
              </div>
            </div>
          </div>

          {liveVehicles.length === 0 ? (
            <div className="vehicle-empty-state">
              <div className="vehicle-empty-icon">⌁</div>
              <strong>No connected vehicles are currently reporting GPS telemetry.</strong>
              <span>Register or connect a vehicle to begin live tracking.</span>
            </div>
          ) : (
            <div className="vehicle-live-grid">
              {liveVehicles.map((vehicle, index) => {
                const latitude = Number(vehicle?.latitude)
                const longitude = Number(vehicle?.longitude)
                const hasCoords = Number.isFinite(latitude) && Number.isFinite(longitude)
                const speed = vehicle?.speed != null ? Number(vehicle.speed) : null
                const isSimulating = simulationRunning && vehicle?.vehicle_id === simulationVehicleId

                return (
                  <div
                    key={vehicle?.vehicle_id || index}
                    className={`vehicle-live-item ${isSimulating ? 'is-simulating' : ''}`}
                  >
                    <div className="vehicle-live-item-top">
                      <div>
                        <span className="vehicle-type-tag">
                          {vehicle?.vehicle_type || 'RESPONSE UNIT'}
                        </span>
                        <strong>{vehicle?.vehicle_id || `Vehicle ${index + 1}`}</strong>
                      </div>
                      <span className={`vehicle-status-pill ${isSimulating ? 'simulating' : ''}`}>
                        <i></i>
                        {isSimulating ? 'SIMULATING' : vehicleStatusLabel(vehicle?.status)}
                      </span>
                    </div>

                    <div className="vehicle-telemetry-grid">
                      <div>
                        <span>LOCATION</span>
                        <strong>{vehicle?.current_location || '—'}</strong>
                      </div>
                      <div>
                        <span>ROAD</span>
                        <strong>{vehicle?.current_road_id || '—'}</strong>
                      </div>
                      <div>
                        <span>SPEED</span>
                        <strong>{Number.isFinite(speed) ? `${speed} km/h` : '—'}</strong>
                      </div>
                      <div>
                        <span>COORDINATES</span>
                        <strong>{hasCoords ? `${latitude.toFixed(4)}, ${longitude.toFixed(4)}` : '—'}</strong>
                      </div>
                    </div>

                    <div className="vehicle-live-footer">
                      <span>
                        <i className="gps-dot"></i>
                        GPS {hasCoords ? 'POSITION LOCKED' : 'UNAVAILABLE'}
                      </span>
                      <span>
                        {vehicle?.last_gps_update
                          ? `UPDATED ${formatGpsUpdate(vehicle.last_gps_update)}`
                          : 'AWAITING GPS UPDATE'}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        {/* INTELLIGENCE */}
        <section className="section-title">

          <span className="label">
            DECISION SUPPORT
          </span>

          <h2>
            Operations Intelligence
          </h2>

        </section>

        <section className="intelligence">

          {/* FIELD */}
          <div className="intel">

            <div className="icon">
              FO
            </div>

            <div>

              <span className="label">
                FIELD OFFICER REPORT
              </span>

              <h3>
                Ground Intelligence
              </h3>

              <p>
                {activeIncidents.length === 0
                  ? 'No active field incidents require immediate review.'
                  : `${activeIncidents.length} active incident${activeIncidents.length === 1 ? '' : 's'} currently require operational review.`}
              </p>

              <div className="intel-summary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginTop: '14px' }}>
                <span>HIGH PRIORITY</span>
                <strong>{activeHighPriorityIncidents.length}</strong>
              </div>

              <button
                type="button"
                onClick={() => setShowReports(true)}
              >
                VIEW REPORTS →
              </button>

            </div>
          </div>

          {/* WEATHER */}
          <div className="intel">

            <div className="icon">
              WX
            </div>

            <div>

              <span className="label">
                WEATHER INTELLIGENCE
              </span>

              <h3>
                {weather?.location ||
                  'Environmental Conditions'}
              </h3>

              {weather ? (

                <>
                  <div className="weather-details">

                    <div>
                      <strong>
                        {weather.weather
                          ?.temperature ?? '—'}
                        °C
                      </strong>

                      <span>
                        TEMPERATURE
                      </span>
                    </div>

                    <div>
                      <strong>
                        {weather.weather
                          ?.rainfall_mm ?? '—'}{' '}
                        mm
                      </strong>

                      <span>
                        RAINFALL
                      </span>
                    </div>

                    <div>
                      <strong>
                        {weather.weather
                          ?.wind_speed_kmh ?? '—'}{' '}
                        km/h
                      </strong>

                      <span>
                        WIND
                      </span>
                    </div>

                    <div>
                      <strong>
                        {weather.weather
                          ?.visibility_km ?? '—'}{' '}
                        km
                      </strong>

                      <span>
                        VISIBILITY
                      </span>
                    </div>

                  </div>

                  <div className="weather-risk">

                    <span>
                      WEATHER RISK
                    </span>

                    <strong>
                      {weather.risk?.level ||
                        '—'}

                      {weatherRisk !== null
                        ? ` · ${weatherRisk}%`
                        : ''}
                    </strong>

                  </div>

                  {weather.risk?.warnings
                    ?.length > 0 ? (

                    <p>
                      {weather.risk.warnings.join(
                        ' • ',
                      )}
                    </p>

                  ) : (

                    <p>
                      No active weather warnings
                      for this location.
                    </p>

                  )}

                </>

              ) : (

                <p>
                  Loading live weather
                  conditions...
                </p>

              )}

              <button onClick={() => setShowWeather(true)}>
                VIEW WEATHER →
              </button>

            </div>
          </div>

          {/* ML */}
          <div className="intel ai-card">

            <div className="icon ai">
              AI
            </div>

            <div>

              <span className="label">
                ML ROAD RISK
              </span>

              <h3>
                AI Risk Prediction
              </h3>

              <div className="risk-line" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '14px' }}>

                <strong>
                  {risk !== null
                    ? `${risk}%`
                    : '—'}
                </strong>

                <span>
                  {recommended?.risk_level ||
                    (mlReady ? 'READY' : 'UNAVAILABLE')}
                </span>

              </div>

              <p>
                {decision?.reason ||
                  (mlReady
                    ? `ML engine ready. ${activeHighPriorityIncidents.length} high-priority incident${activeHighPriorityIncidents.length === 1 ? '' : 's'} detected across the network.`
                    : 'ML engine is not reporting READY status.')}
              </p>

              <div className="intel-summary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginTop: '14px' }}>
                <span>CONNECTED FLEET</span>
                <strong>{activeVehicleCount}</strong>
              </div>

              <button
                onClick={planRoute}
              >
                {routeLoading
                  ? 'ANALYZING...'
                  : 'RUN AI ANALYSIS →'}
              </button>

            </div>
          </div>

          {/* ROUTE */}
          <div className="intel route-card">

            <div className="icon">
              RT
            </div>

            <div className="route-content">

              <span className="label">
                ROUTE / REROUTE
              </span>

              <h3>
                AI Route Planner
              </h3>

              <div className="route-inputs">

                <div>

                  <label>
                    FROM
                  </label>

                  <select
                    value={from}
                    onChange={(e) => setFrom(e.target.value)}
                    disabled={routeLocationOptions.length === 0}
                    aria-label="Route start location"
                    style={{ width: '100%' }}
                  >
                    {routeLocationOptions.length === 0 ? (
                      <option value={from}>Loading network locations...</option>
                    ) : (
                      routeLocationOptions.map((option) => (
                        <option key={`from-${option.value}`} value={option.value}>
                          {option.label}
                        </option>
                      ))
                    )}
                  </select>

                </div>

                <span className="arrow">
                  →
                </span>

                <div>

                  <label>
                    TO
                  </label>

                  <select
                    value={to}
                    onChange={(e) => setTo(e.target.value)}
                    disabled={routeLocationOptions.length === 0}
                    aria-label="Route destination"
                    style={{ width: '100%' }}
                  >
                    {routeLocationOptions.length === 0 ? (
                      <option value={to}>Loading network locations...</option>
                    ) : (
                      routeLocationOptions.map((option) => (
                        <option key={`to-${option.value}`} value={option.value}>
                          {option.label}
                        </option>
                      ))
                    )}
                  </select>

                </div>

              </div>

              {routeLocationOptions.length > 0 && (
                <p style={{ margin: '10px 0 0', fontSize: '12px', opacity: 0.72 }}>
                  Using {routeLocationOptions.length} live network locations from the backend.
                </p>
              )}

              {activeIncidents.length > 0 && (
                <div style={{
                  marginTop: '12px',
                  padding: '12px 14px',
                  border: '1px solid rgba(248,113,113,.28)',
                  borderRadius: '12px',
                  background: 'rgba(127,29,29,.16)',
                }}>
                  <div style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '.08em', color: '#fca5a5' }}>
                    LIVE INCIDENT REROUTING
                  </div>
                  <div style={{ marginTop: '4px', fontSize: '12px', lineHeight: 1.5 }}>
                    {activeIncidents.length} active incident{activeIncidents.length === 1 ? '' : 's'} · blocked roads are included automatically in the backend route decision.
                  </div>
                  {incidentRouteStatus && (
                    <div style={{ marginTop: '6px', fontSize: '11px', opacity: .78 }}>
                      {incidentRouteStatus}
                    </div>
                  )}
                </div>
              )}

              <button
                className="plan-button"
                onClick={planRoute}
                disabled={routeLoading || !from || !to || from === to}
              >
                {routeLoading
                  ? 'PLANNING ROUTE...'
                  : 'PLAN ROUTE'}
              </button>

              {routeError && (
                <div className="error">
                  {routeError}
                </div>
              )}

              {recommended && (

                <div className="route-result">

                  <div className="route-top">

                    <div>

                      <span>
                        RECOMMENDED ROUTE
                      </span>

                      <b>
                        {route.start_location}
                        {' → '}
                        {route.destination_location}
                      </b>

                    </div>

                    <strong className="high">
                      {recommended.risk_level}
                    </strong>

                  </div>

                  {route?.source && (
                    <div style={{ marginTop: '10px', fontSize: '12px', opacity: 0.72 }}>
                      Route engine: {String(route.source)}
                    </div>
                  )}

                  {activeBlockedRoads.length > 0 && (
                    <div style={{
                      marginTop: '10px',
                      padding: '10px 12px',
                      borderRadius: '10px',
                      background: 'rgba(248,113,113,.10)',
                      border: '1px solid rgba(248,113,113,.22)',
                    }}>
                      <div style={{ fontSize: '10px', fontWeight: 800, letterSpacing: '.08em', color: '#fca5a5' }}>
                        ACTIVE BLOCKED ROADS
                      </div>
                      <div style={{ marginTop: '4px', fontSize: '12px', fontWeight: 700 }}>
                        {activeBlockedRoads.join(', ')}
                      </div>
                      <div style={{ marginTop: '4px', fontSize: '11px', opacity: .72 }}>
                        ML route selection is evaluated with these roads blocked.
                      </div>
                    </div>
                  )}

                  <div style={{ marginTop: '8px', fontSize: '12px', opacity: 0.78 }}>
                    {gisRouteLoading
                      ? 'GIS: calculating actual road geometry…'
                      : gisRoute
                        ? `ML network path: ${gisRoute.distanceKm.toFixed(1)} km · ${Math.round(gisRoute.durationMinutes)} min`
                        : gisRouteError
                          ? `GIS geometry unavailable: ${gisRouteError}`
                          : 'GIS road geometry not loaded yet.'}
                  </div>

                  <div className="route-risk">

                    <div>

                      <strong>
                        {risk}%
                      </strong>

                      <span>
                        PREDICTED RISK
                      </span>

                    </div>

                    <div>

                      <strong>
                        {decision?.recommendation}
                      </strong>

                      <span>
                        AI DECISION
                      </span>

                    </div>

                  </div>

                  <div className="route-details">

                    <div>
                      <span>
                        ROAD
                      </span>

                      <b>
                        {recommended.road_ids?.join(
                          ', ',
                        ) || 'N/A'}
                      </b>
                    </div>

                    <div>
                      <span>
                        DISTANCE
                      </span>

                      <b>
                        {recommended.distance_km}{' '}
                        km
                      </b>
                    </div>

                    <div>
                      <span>
                        TRAVEL TIME
                      </span>

                      <b>
                        {
                          recommended
                            .estimated_travel_time_hours
                        }{' '}
                        hrs
                      </b>
                    </div>

                    <div>
                      <span>
                        DELAY
                      </span>

                      <b>
                        {
                          recommended
                            .estimated_delay_hours
                        }{' '}
                        hrs
                      </b>
                    </div>

                  </div>

                  {activeBlockedRoads.length >
                    0 && (

                    <div className="blocked">

                      <span>
                        ACTIVE BLOCKAGES
                      </span>

                      <b>
                        {activeBlockedRoads.join(
                          ', ',
                        )}
                      </b>

                    </div>

                  )}

                  <div className="assessment">

                    <span>
                      AI ASSESSMENT
                    </span>

                    <p>
                      {decision?.reason}
                    </p>

                  </div>

                </div>

              )}

            </div>
          </div>

        </section>

        {/* QUICK ACTIONS */}
        <section className="section-title quick-title">

          <span className="label">
            OPERATIONS
          </span>

          <h2>
            Quick Actions
          </h2>

        </section>

        <section className="quick">

          <button
            onClick={() => {
              setShowIncidentForm(true)
              setIncidentMessage('')
              setIncidentError('')
            }}
          >
            <span>+</span>
            REPORT INCIDENT
          </button>

          <button
            onClick={() => {
              setShowVehicleForm(true)
              setVehicleMessage('')
              setVehicleError('')
            }}
          >
            <span>+</span>
            REGISTER VEHICLE
          </button>

          <button onClick={planRoute}>
            <span>→</span>
            PLAN ROUTE
          </button>

          <button
            onClick={refreshData}
            disabled={refreshLoading || !token}
          >
            <span className={refreshLoading ? 'refresh-spin' : ''}>
              ↻
            </span>
            {refreshLoading ? 'REFRESHING...' : 'REFRESH DATA'}
          </button>

        </section>

        {(refreshMessage || refreshError) && (
          <div
            className={
              refreshError
                ? 'refresh-status refresh-error'
                : 'refresh-status'
            }
          >
            {refreshError || refreshMessage}
          </div>
        )}

      </main>

      {/* INCIDENT MODAL */}
      {showIncidentForm && (

        <div
          className="modal-overlay"
          onClick={() =>
            !incidentLoading &&
            setShowIncidentForm(false)
          }
        >

          <div
            className="incident-modal"
            onClick={(e) =>
              e.stopPropagation()
            }
          >

            <div className="modal-header">

              <div>
                <span className="label">
                  FIELD REPORTING
                </span>

                <h2>
                  Report Incident
                </h2>
              </div>

              <button
                className="modal-close"
                onClick={() =>
                  !incidentLoading &&
                  setShowIncidentForm(false)
                }
              >
                ×
              </button>

            </div>

            <form
              onSubmit={reportIncident}
              className="incident-form"
            >

              <div className="form-row">

                <div className="form-group">

                  <label>
                    INCIDENT TYPE
                  </label>

                  <select
                    name="incident_type"
                    value={
                      incidentForm.incident_type
                    }
                    onChange={
                      handleIncidentChange
                    }
                  >
                    <option>
                      ROAD BLOCKAGE
                    </option>

                    <option>
                      ACCIDENT
                    </option>

                    <option>
                      FLOOD
                    </option>

                    <option>
                      LANDSLIDE
                    </option>

                    <option>
                      VEHICLE BREAKDOWN
                    </option>

                    <option>
                      WEATHER HAZARD
                    </option>

                    <option>
                      OTHER
                    </option>
                  </select>

                </div>

                <div className="form-group">

                  <label>
                    SEVERITY
                  </label>

                  <select
                    name="severity"
                    value={
                      incidentForm.severity
                    }
                    onChange={
                      handleIncidentChange
                    }
                  >
                    <option>
                      LOW
                    </option>

                    <option>
                      MEDIUM
                    </option>

                    <option>
                      HIGH
                    </option>

                    <option>
                      CRITICAL
                    </option>
                  </select>

                </div>

              </div>

              <div className="form-row">

                <div className="form-group">

                  <label>
                    LOCATION *
                  </label>

                  <input
                    name="location"
                    value={
                      incidentForm.location
                    }
                    onChange={
                      handleIncidentChange
                    }
                    placeholder="e.g. Tawang"
                    required
                  />

                </div>

                <div className="form-group">

                  <label>
                    ROAD ID
                  </label>

                  <input
                    name="road_id"
                    value={
                      incidentForm.road_id
                    }
                    onChange={
                      handleIncidentChange
                    }
                    placeholder="e.g. NH13"
                  />

                </div>

              </div>

              <div className="form-group">

                <label>
                  DESCRIPTION
                </label>

                <textarea
                  name="description"
                  value={
                    incidentForm.description
                  }
                  onChange={
                    handleIncidentChange
                  }
                  placeholder="Describe the incident..."
                  rows="3"
                />

              </div>

              <div className="form-row">

                <div className="form-group">

                  <label>
                    LATITUDE
                  </label>

                  <input
                    name="latitude"
                    type="number"
                    step="any"
                    value={
                      incidentForm.latitude
                    }
                    onChange={
                      handleIncidentChange
                    }
                    placeholder="e.g. 27.5861"
                  />

                </div>

                <div className="form-group">

                  <label>
                    LONGITUDE
                  </label>

                  <input
                    name="longitude"
                    type="number"
                    step="any"
                    value={
                      incidentForm.longitude
                    }
                    onChange={
                      handleIncidentChange
                    }
                    placeholder="e.g. 91.8594"
                  />

                </div>

              </div>

              {incidentError && (
                <div className="error">
                  {incidentError}
                </div>
              )}

              {incidentMessage && (
                <div className="success-message">
                  {incidentMessage}
                </div>
              )}

              <div className="form-actions">

                <button
                  type="button"
                  className="cancel-button"
                  onClick={() =>
                    !incidentLoading &&
                    setShowIncidentForm(false)
                  }
                  disabled={incidentLoading}
                >
                  CANCEL
                </button>

                <button
                  type="submit"
                  className="submit-button"
                  disabled={incidentLoading}
                >
                  {incidentLoading
                    ? 'REPORTING...'
                    : 'REPORT INCIDENT →'}
                </button>

              </div>

            </form>

          </div>
        </div>

      )}

      {/* REPORTS MODAL */}
      {showReports && (
        <div
          className="modal-overlay"
          onClick={() => setShowReports(false)}
        >
          <div
            className="modal reports-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <span className="label">FIELD OFFICER REPORTS</span>
                <h2>Incident Reports</h2>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setShowReports(false)}
              >
                ×
              </button>
            </div>

            <div className="reports-summary">
              <div>
                <span>TOTAL REPORTS</span>
                <strong>{incidents.length}</strong>
              </div>
              <div>
                <span>ACTIVE</span>
                <strong>
                  {incidents.filter((item) => item.status !== 'RESOLVED').length}
                </strong>
              </div>
              <div>
                <span>RESOLVED</span>
                <strong>
                  {incidents.filter((item) => item.status === 'RESOLVED').length}
                </strong>
              </div>
            </div>

            <div className="reports-list">
              {activeIncidents.length === 0 ? (
                <div className="empty report-empty">
                  No incident reports available.
                </div>
              ) : (
                activeIncidents.map((item) => (
                  <div className="report-item" key={item.incident_id}>
                    <div className="report-top">
                      <div>
                        <span className={`severity ${String(item.severity || '').toLowerCase()}`}></span>
                        <strong>{item.incident_type || 'INCIDENT'}</strong>
                      </div>
                      <span className={`report-status ${item.status === 'RESOLVED' ? 'resolved' : 'active'}`}>
                        {item.status || 'ACTIVE'}
                      </span>
                    </div>

                    <div className="report-grid">
                      <div><span>LOCATION</span><strong>{item.location || 'N/A'}</strong></div>
                      <div><span>ROAD</span><strong>{item.road_id || 'N/A'}</strong></div>
                      <div><span>SEVERITY</span><strong>{item.severity || 'N/A'}</strong></div>
                      <div><span>REPORTED</span><strong>{item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A'}</strong></div>
                    </div>

                    {item.description && (
                      <p className="report-description">{item.description}</p>
                    )}

                    {item.latitude != null && item.longitude != null && (
                      <small className="report-coordinates">
                        Coordinates: {item.latitude}, {item.longitude}
                      </small>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* VEHICLE REGISTRATION MODAL */}
      {showVehicleForm && (

        <div
          className="modal-overlay"
          onClick={() =>
            !vehicleLoading &&
            setShowVehicleForm(false)
          }
        >

          <div
            className="incident-modal vehicle-modal"
            onClick={(e) =>
              e.stopPropagation()
            }
          >

            <div className="modal-header">

              <div>
                <span className="label">
                  FLEET MANAGEMENT
                </span>

                <h2>
                  Register Vehicle
                </h2>
              </div>

              <button
                className="modal-close"
                onClick={() =>
                  !vehicleLoading &&
                  setShowVehicleForm(false)
                }
              >
                ×
              </button>

            </div>

            <form
              onSubmit={registerVehicle}
              className="incident-form"
            >

              <div className="form-row">

                <div className="form-group">

                  <label>
                    VEHICLE TYPE *
                  </label>

                  <select
                    name="vehicle_type"
                    value={vehicleForm.vehicle_type}
                    onChange={handleVehicleChange}
                    required
                  >
                    <option>RESCUE TRUCK</option>
                    <option>AMBULANCE</option>
                    <option>SUPPLY TRUCK</option>
                    <option>COMMAND VEHICLE</option>
                    <option>UTILITY VEHICLE</option>
                    <option>OTHER</option>
                  </select>

                </div>

                <div className="form-group">

                  <label>
                    DRIVER NAME
                  </label>

                  <input
                    name="driver_name"
                    value={vehicleForm.driver_name}
                    onChange={handleVehicleChange}
                    placeholder="e.g. Ravi Kumar"
                  />

                </div>

              </div>

              <div className="form-row">

                <div className="form-group">

                  <label>
                    CARGO TYPE
                  </label>

                  <input
                    name="cargo_type"
                    value={vehicleForm.cargo_type}
                    onChange={handleVehicleChange}
                    placeholder="e.g. Emergency Supplies"
                  />

                </div>

                <div className="form-group">

                  <label>
                    CURRENT LOCATION *
                  </label>

                  <input
                    name="current_location"
                    value={vehicleForm.current_location}
                    onChange={handleVehicleChange}
                    placeholder="e.g. Tawang"
                    required
                  />

                </div>

              </div>

              <div className="form-row">

                <div className="form-group">

                  <label>
                    ROAD ID
                  </label>

                  <input
                    name="current_road_id"
                    value={vehicleForm.current_road_id}
                    onChange={handleVehicleChange}
                    placeholder="e.g. NH13"
                  />

                </div>

                <div className="form-group">

                  <label>
                    SPEED (KM/H)
                  </label>

                  <input
                    name="speed"
                    type="number"
                    min="0"
                    step="any"
                    value={vehicleForm.speed}
                    onChange={handleVehicleChange}
                    placeholder="e.g. 42"
                  />

                </div>

              </div>

              <div className="form-row">

                <div className="form-group">

                  <label>
                    LATITUDE
                  </label>

                  <input
                    name="latitude"
                    type="number"
                    step="any"
                    value={vehicleForm.latitude}
                    onChange={handleVehicleChange}
                    placeholder="e.g. 27.5860"
                  />

                </div>

                <div className="form-group">

                  <label>
                    LONGITUDE
                  </label>

                  <input
                    name="longitude"
                    type="number"
                    step="any"
                    value={vehicleForm.longitude}
                    onChange={handleVehicleChange}
                    placeholder="e.g. 91.8650"
                  />

                </div>

              </div>

              {vehicleError && (
                <div className="error">
                  {vehicleError}
                </div>
              )}

              {vehicleMessage && (
                <div className="success-message">
                  {vehicleMessage}
                </div>
              )}

              <div className="form-actions">

                <button
                  type="button"
                  className="cancel-button"
                  onClick={() =>
                    !vehicleLoading &&
                    setShowVehicleForm(false)
                  }
                  disabled={vehicleLoading}
                >
                  CANCEL
                </button>

                <button
                  type="submit"
                  className="submit-button"
                  disabled={vehicleLoading}
                >
                  {vehicleLoading
                    ? 'REGISTERING...'
                    : 'REGISTER VEHICLE →'}
                </button>

              </div>

            </form>

          </div>
        </div>

      )}

      {/* WEATHER MODAL */}
      {showWeather && (
        <div
          className="modal-overlay"
          onClick={() => setShowWeather(false)}
        >
          <div
            className="modal weather-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <span className="label">WEATHER INTELLIGENCE</span>
                <h2>{weather?.location || 'Weather Details'}</h2>
              </div>

              <button
                type="button"
                className="modal-close"
                onClick={() => setShowWeather(false)}
              >
                ×
              </button>
            </div>

            {weather ? (
              <>
                <div className="weather-modal-grid">
                  <div className="weather-modal-stat">
                    <span>TEMPERATURE</span>
                    <strong>{weather.weather?.temperature ?? '—'}°C</strong>
                  </div>
                  <div className="weather-modal-stat">
                    <span>RAINFALL</span>
                    <strong>{weather.weather?.rainfall_mm ?? '—'} mm</strong>
                  </div>
                  <div className="weather-modal-stat">
                    <span>WIND SPEED</span>
                    <strong>{weather.weather?.wind_speed_kmh ?? '—'} km/h</strong>
                  </div>
                  <div className="weather-modal-stat">
                    <span>VISIBILITY</span>
                    <strong>{weather.weather?.visibility_km ?? '—'} km</strong>
                  </div>
                </div>

                <div className="weather-modal-risk">
                  <span>WEATHER RISK</span>
                  <strong>
                    {weather.risk?.level || '—'}
                    {weatherRisk !== null ? ` · ${weatherRisk}%` : ''}
                  </strong>
                </div>

                <div className="weather-modal-warning">
                  <span>ACTIVE WARNINGS</span>
                  {weather.risk?.warnings?.length > 0 ? (
                    <ul>
                      {weather.risk.warnings.map((warning, index) => (
                        <li key={index}>{warning}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No active weather warnings for this location.</p>
                  )}
                </div>
              </>
            ) : (
              <div className="weather-loading">
                Loading live weather conditions...
              </div>
            )}

            <div className="form-actions">
              <button
                type="button"
                className="cancel-button"
                onClick={() => setShowWeather(false)}
              >
                CLOSE
              </button>
            </div>
          </div>
        </div>
      )}

      {/* FOOTER */}
      <footer>

        <span>
          NER-RESQ | SMART LOGISTICS PLATFORM
        </span>

        <span>
          BACKEND CONNECTED
          <i></i>
          ML ENGINE READY
        </span>

      </footer>

      </div>
    )
  )
}

export default App