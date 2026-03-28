import { useEffect, useRef } from 'react'
import type { VenueCoordinate } from '../../api/types'

interface Props {
  venues: VenueCoordinate[]
}

// Colours for up to 7 days — cycles if longer
const DAY_COLOURS = ['#4f86f7', '#34c77b', '#f59e0b', '#ef4444', '#a855f7', '#ec4899', '#14b8a6']

function dayColour(day: number) {
  return DAY_COLOURS[(day - 1) % DAY_COLOURS.length]
}

export default function ItineraryMap({ venues }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<unknown>(null)

  useEffect(() => {
    if (!containerRef.current || venues.length === 0) return
    // Leaflet must be imported dynamically — it accesses `window` and breaks SSR
    let L: typeof import('leaflet')
    let mapInstance: ReturnType<typeof import('leaflet')['map']> | null = null

    import('leaflet').then(mod => {
      L = mod.default ?? mod

      // Fix default marker icon paths broken by Vite's asset pipeline
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (L.Icon.Default.prototype as any)._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      })

      if (!containerRef.current) return
      // Destroy previous map instance if re-rendering
      if (mapRef.current) {
        ;(mapRef.current as ReturnType<typeof L.map>).remove()
        mapRef.current = null
      }

      mapInstance = L.map(containerRef.current)
      mapRef.current = mapInstance

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(mapInstance)

      // Group venues by day for route lines
      const byDay: Record<number, VenueCoordinate[]> = {}
      for (const v of venues) {
        if (!byDay[v.day]) byDay[v.day] = []
        byDay[v.day].push(v)
      }

      const allLatLngs: [number, number][] = []

      for (const [dayStr, dayVenues] of Object.entries(byDay)) {
        const day = Number(dayStr)
        const colour = dayColour(day)
        const latLngs: [number, number][] = dayVenues.map(v => [v.lat, v.lon])

        // Route polyline for this day
        if (latLngs.length > 1) {
          L.polyline(latLngs, { color: colour, weight: 2.5, opacity: 0.7, dashArray: '6 4' })
            .addTo(mapInstance)
        }

        // Numbered markers
        dayVenues.forEach((v, idx) => {
          const html = `
            <div style="
              background:${colour};color:#fff;border-radius:50%;
              width:28px;height:28px;display:flex;align-items:center;
              justify-content:center;font-weight:700;font-size:12px;
              border:2px solid rgba(0,0,0,0.25);box-shadow:0 1px 4px rgba(0,0,0,0.3);
            ">${idx + 1}</div>`
          const icon = L.divIcon({ html, className: '', iconSize: [28, 28], iconAnchor: [14, 14] })

          L.marker([v.lat, v.lon], { icon })
            .addTo(mapInstance!)
            .bindPopup(`
              <div style="font-family:sans-serif;min-width:140px">
                <div style="font-weight:700;margin-bottom:4px">${v.name}</div>
                <div style="color:#666;font-size:12px">
                  <span style="background:${colour};color:#fff;border-radius:3px;padding:1px 6px;font-size:11px">
                    Day ${v.day}
                  </span>
                  &nbsp;${v.time}
                </div>
              </div>
            `)

          allLatLngs.push([v.lat, v.lon])
        })
      }

      // Fit map to all venues
      if (allLatLngs.length > 0) {
        mapInstance.fitBounds(allLatLngs, { padding: [32, 32] })
      }
    })

    return () => {
      if (mapRef.current) {
        ;(mapRef.current as ReturnType<typeof import('leaflet')['map']>).remove()
        mapRef.current = null
      }
    }
  }, [venues])

  if (venues.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 bg-base-300 rounded-xl text-base-content/40 text-sm">
        No location data available for this itinerary.
      </div>
    )
  }

  // Collect unique days for the legend
  const days = [...new Set(venues.map(v => v.day))].sort((a, b) => a - b)

  return (
    <div className="flex flex-col gap-3">
      {/* Legend */}
      <div className="flex flex-wrap gap-2">
        {days.map(d => (
          <span
            key={d}
            className="text-xs px-2.5 py-1 rounded-full font-medium text-white"
            style={{ background: dayColour(d) }}
          >
            Day {d}
          </span>
        ))}
      </div>

      {/* Map */}
      <div
        ref={containerRef}
        className="w-full rounded-xl overflow-hidden border border-base-300"
        style={{ height: '420px' }}
      />
    </div>
  )
}
