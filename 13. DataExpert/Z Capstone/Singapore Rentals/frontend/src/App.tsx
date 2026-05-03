import { useState, useEffect } from 'react'
import { Navbar } from './components/Layout/Navbar'
import type { Tab } from './components/Layout/Navbar'
import { FilterBar } from './components/Layout/FilterBar'
import { LandingPage } from './components/Layout/LandingPage'
import { MapView } from './components/Map/MapView'
import { ChartsView } from './components/Charts/ChartsView'
import { ContractsTable } from './components/Table/ContractsTable'
import { SavedView } from './components/Saved/SavedView'
import { useFilters } from './hooks/useFilters'
import { useQuery } from './hooks/useQuery'
import { api } from './lib/api'
import type { MrtStation } from './types'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('home')
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('darkMode') === 'true'
  })

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', String(darkMode))
  }, [darkMode])

  const { filters, updateFilter, toggleArrayItem, addBuilding, removeBuilding, resetFilters, hasActiveFilters } = useFilters()

  const { data: allStations } = useQuery<MrtStation[]>(
    () => api.stations() as Promise<MrtStation[]>,
    [],
  )

  const sharedFilterProps = {
    filters,
    allStations: allStations ?? [],
    onToggleArrayItem: toggleArrayItem,
    onUpdateFilter: updateFilter,
    onAddBuilding: addBuilding,
    onRemoveBuilding: removeBuilding,
    onReset: resetFilters,
    hasActiveFilters,
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white overflow-hidden">
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onHome={() => setActiveTab('home')}
        darkMode={darkMode}
        onToggleDark={() => setDarkMode(d => !d)}
      />

      {activeTab !== 'home' && (
        <FilterBar {...sharedFilterProps} />
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        {activeTab === 'home' && (
          <LandingPage
            {...sharedFilterProps}
            onSearch={() => setActiveTab('charts')}
          />
        )}
        {activeTab === 'charts' && <ChartsView filters={filters} />}
        {activeTab === 'map' && <MapView filters={filters} />}
        {activeTab === 'saved' && <SavedView />}
        {activeTab === 'table' && <ContractsTable filters={filters} />}
        {activeTab === 'ai' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-gray-400 dark:text-gray-500">
            <span className="text-5xl">✨</span>
            <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">AI Magic</p>
            <p className="text-sm">Coming soon.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
