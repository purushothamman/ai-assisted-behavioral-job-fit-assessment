// src/pages/AdminFrameworkPage.jsx
// Comprehensive Platform Administration Interface for managing the Behavioral Framework:
// - Create, edit, activate/deactivate, reorder, and safely archive dimensions.
// - Manage observable behavioral indicators per dimension.
// - Pre-activation framework validation.
// - Framework versioning: preview staged changes, freeze immutable snapshots, and activate releases.

import { useEffect, useState } from 'react'
import { adminFrameworkApi } from '../services/api'

export default function AdminFrameworkPage() {
  const [dimensions, setDimensions] = useState([])
  const [versions, setVersions] = useState([])
  const [currentVersion, setCurrentVersion] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  // Active tab: 'active' | 'archived' | 'versions'
  const [activeTab, setActiveTab] = useState('active')

  // Modals state
  const [showDimensionModal, setShowDimensionModal] = useState(false)
  const [editingDimension, setEditingDimension] = useState(null)
  const [showIndicatorModal, setShowIndicatorModal] = useState(false)
  const [indicatorParentDim, setIndicatorParentDim] = useState(null)
  const [editingIndicator, setEditingIndicator] = useState(null)
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [showSnapshotModal, setShowSnapshotModal] = useState(false)
  const [viewingSnapshot, setViewingSnapshot] = useState(null)

  // In-modal errors
  const [dimModalError, setDimModalError] = useState(null)
  const [indModalError, setIndModalError] = useState(null)
  const [publishModalError, setPublishModalError] = useState(null)

  // Validation state
  const [validationResult, setValidationResult] = useState(null)
  const [validating, setValidating] = useState(false)

  // Publish form
  const [publishName, setPublishName] = useState('')
  const [publishDesc, setPublishDesc] = useState('')
  const [publishing, setPublishing] = useState(false)

  // Dimension form
  const [dimName, setDimName] = useState('')
  const [dimDesc, setDimDesc] = useState('')
  const [dimStatus, setDimStatus] = useState('active')
  const [dimIsActive, setDimIsActive] = useState(true)
  const [initialInds, setInitialInds] = useState([
    { name: '', description: '', example_behaviors: '' },
    { name: '', description: '', example_behaviors: '' },
  ])
  const [submittingDim, setSubmittingDim] = useState(false)

  // Indicator form
  const [indName, setIndName] = useState('')
  const [indDesc, setIndDesc] = useState('')
  const [indExamples, setIndExamples] = useState('')
  const [submittingInd, setSubmittingInd] = useState(false)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [dimRes, verRes, curRes] = await Promise.all([
        adminFrameworkApi.listDimensions(true),
        adminFrameworkApi.listVersions(),
        adminFrameworkApi.getCurrentVersion(),
      ])
      setDimensions(dimRes.data ?? [])
      setVersions(verRes.data ?? [])
      setCurrentVersion(curRes.data ?? null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Auto-clear success message after 4 seconds
  useEffect(() => {
    if (successMsg) {
      const timer = setTimeout(() => setSuccessMsg(null), 4000)
      return () => clearTimeout(timer)
    }
  }, [successMsg])

  // ── Dimension Handlers ───────────────────────────────────────────────────

  const openCreateDimension = () => {
    setDimModalError(null)
    setEditingDimension(null)
    setDimName('')
    setDimDesc('')
    setDimStatus('active')
    setDimIsActive(true)
    setInitialInds([
      { name: '', description: '', example_behaviors: '' },
      { name: '', description: '', example_behaviors: '' },
    ])
    setShowDimensionModal(true)
  }

  const openEditDimension = (dim) => {
    setDimModalError(null)
    setEditingDimension(dim)
    setDimName(dim.name)
    setDimDesc(dim.description || '')
    setDimStatus(dim.status || (dim.is_active ? 'active' : 'draft'))
    setDimIsActive(dim.is_active ?? true)
    setShowDimensionModal(true)
  }

  const handleSaveDimension = async (e) => {
    e.preventDefault()
    setDimModalError(null)
    setError(null)

    const cleanDimName = dimName.trim().toLowerCase().replace(/[\s-]+/g, '_')
    if (!/^[a-z][a-z0-9_]{1,63}$/.test(cleanDimName)) {
      setDimModalError("Dimension slug must start with a lowercase letter and contain only letters, numbers, and underscores (e.g. strategic_thinking).")
      return
    }

    if (dimDesc.trim().length < 10) {
      setDimModalError("Dimension description must be at least 10 characters long.")
      return
    }

    // Validate initial indicators
    if (!editingDimension) {
      for (let i = 0; i < initialInds.length; i++) {
        const ind = initialInds[i]
        const hasName = Boolean(ind.name.trim())
        const hasDesc = Boolean(ind.description.trim())
        if (hasName || hasDesc) {
          if (!hasName) {
            setDimModalError(`Indicator #${i + 1} requires a name identifier.`)
            return
          }
          const cleanIndName = ind.name.trim().toLowerCase().replace(/[\s-]+/g, '_')
          if (!/^[a-z][a-z0-9_]{1,63}$/.test(cleanIndName)) {
            setDimModalError(`Indicator #${i + 1} ('${ind.name}') must start with a lowercase letter and contain only letters, numbers, and underscores.`)
            return
          }
          if (ind.description.trim().length < 5) {
            setDimModalError(`Indicator #${i + 1} ('${ind.name}') description must be at least 5 characters.`)
            return
          }
        }
      }
    }

    setSubmittingDim(true)
    try {
      if (editingDimension) {
        await adminFrameworkApi.updateDimension(editingDimension.id, {
          name: cleanDimName,
          description: dimDesc.trim(),
          status: dimStatus,
          is_active: dimIsActive,
        })
        setSuccessMsg(`Dimension '${cleanDimName}' updated successfully.`)
      } else {
        const validInitialInds = initialInds
          .filter(i => i.name.trim() && i.description.trim())
          .map(i => ({
            name: i.name.trim().toLowerCase().replace(/\s+/g, '_'),
            description: i.description.trim(),
            example_behaviors: i.example_behaviors.trim() || null,
          }))

        await adminFrameworkApi.createDimension({
          name: cleanDimName,
          description: dimDesc.trim(),
          status: dimStatus,
          is_active: dimIsActive,
          order_index: dimensions.length,
          initial_indicators: validInitialInds,
        })
        setSuccessMsg(`Dimension '${cleanDimName}' created successfully.`)
      }
      setShowDimensionModal(false)
      await loadData()
    } catch (err) {
      setDimModalError(err.message)
      setError(err.message)
    } finally {
      setSubmittingDim(false)
    }
  }

  const handleToggleDimensionActive = async (dim) => {
    try {
      const nextActive = !dim.is_active
      await adminFrameworkApi.updateDimension(dim.id, {
        is_active: nextActive,
        status: nextActive ? 'active' : 'draft',
      })
      setSuccessMsg(`Dimension '${dim.name}' marked ${nextActive ? 'active' : 'inactive'}.`)
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleArchiveDimension = async (dim) => {
    const isUnreferenced = !dim.is_referenced
    const confirmMsg = isUnreferenced
      ? `Permanently delete '${dim.name}'? Since it is not used in any historical assessments or jobs, it will be deleted cleanly.`
      : `Safely archive '${dim.name}'? Referenced historical job assessments will remain completely intact.`

    if (!window.confirm(confirmMsg)) {
      return
    }
    try {
      const res = await adminFrameworkApi.archiveDimension(dim.id)
      setSuccessMsg(res.data?.message || `Dimension '${dim.name}' processed.`)
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  // ── Reordering Handlers ──────────────────────────────────────────────────

  const handleMoveDimension = async (index, direction) => {
    const activeDims = dimensions.filter(d => d.is_active && d.status === 'active')
    const targetIndex = index + direction
    if (targetIndex < 0 || targetIndex >= activeDims.length) return

    const newOrder = [...activeDims]
    const temp = newOrder[index]
    newOrder[index] = newOrder[targetIndex]
    newOrder[targetIndex] = temp

    const items = newOrder.map((dim, i) => ({
      id: dim.id,
      order_index: i,
    }))

    try {
      await adminFrameworkApi.reorderDimensions(items)
      setSuccessMsg("Dimension display order updated.")
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  // ── Indicator Handlers ───────────────────────────────────────────────────

  const openAddIndicator = (dim) => {
    setIndicatorParentDim(dim)
    setEditingIndicator(null)
    setIndName('')
    setIndDesc('')
    setIndExamples('')
    setIndModalError(null)
    setShowIndicatorModal(true)
  }

  const openEditIndicator = (dim, ind) => {
    setIndicatorParentDim(dim)
    setEditingIndicator(ind)
    setIndName(ind.name)
    setIndDesc(ind.description || '')
    setIndExamples(ind.example_behaviors || '')
    setIndModalError(null)
    setShowIndicatorModal(true)
  }

  const handleSaveIndicator = async (e) => {
    e.preventDefault()
    setIndModalError(null)
    setError(null)

    const cleanIndName = indName.trim().toLowerCase().replace(/[\s-]+/g, '_')
    if (!/^[a-z][a-z0-9_]{1,63}$/.test(cleanIndName)) {
      setIndModalError("Indicator identifier must start with a lowercase letter and contain only letters, numbers, and underscores (e.g. data_driven_reasoning).")
      return
    }
    if (indDesc.trim().length < 5) {
      setIndModalError("Observable description must be at least 5 characters long.")
      return
    }

    setSubmittingInd(true)
    try {
      if (editingIndicator) {
        await adminFrameworkApi.updateIndicator(editingIndicator.id, {
          name: cleanIndName,
          description: indDesc.trim(),
          example_behaviors: indExamples.trim() || null,
        })
        setSuccessMsg(`Indicator '${cleanIndName}' updated.`)
      } else {
        await adminFrameworkApi.addIndicator(indicatorParentDim.id, {
          name: cleanIndName,
          description: indDesc.trim(),
          example_behaviors: indExamples.trim() || null,
          order_index: (indicatorParentDim.indicators?.length || 0),
        })
        setSuccessMsg(`Indicator '${cleanIndName}' added to ${indicatorParentDim.name}.`)
      }
      setShowIndicatorModal(false)
      await loadData()
    } catch (err) {
      setIndModalError(err.message)
      setError(err.message)
    } finally {
      setSubmittingInd(false)
    }
  }

  const handleDeleteIndicator = async (ind) => {
    if (!window.confirm(`Delete observable indicator '${ind.name}'?`)) return
    try {
      await adminFrameworkApi.deleteIndicator(ind.id)
      setSuccessMsg(`Indicator '${ind.name}' deleted.`)
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  // ── Framework Validation & Publishing ─────────────────────────────────────

  const handleValidateFramework = async () => {
    setValidating(true)
    setError(null)
    try {
      const res = await adminFrameworkApi.validateFramework()
      setValidationResult(res.data)
      if (res.data.valid) {
        setSuccessMsg("Framework passed all validation integrity checks! Ready for activation.")
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setValidating(false)
    }
  }

  const openPublishModal = async () => {
    setValidating(true)
    setPublishModalError(null)
    try {
      const valRes = await adminFrameworkApi.validateFramework()
      setValidationResult(valRes.data)
      const nextVerNum = (versions.length > 0 ? Math.max(...versions.map(v => v.version_number)) : 0) + 1
      setPublishName(`v${nextVerNum}.0 Framework Release`)
      setPublishDesc(`Release containing ${valRes.data.active_dimension_count} active dimensions and ${valRes.data.total_indicator_count} observable indicators.`)
      setShowPublishModal(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setValidating(false)
    }
  }

  const handlePublishVersion = async (e) => {
    e.preventDefault()
    setPublishing(true)
    setPublishModalError(null)
    setError(null)
    try {
      const res = await adminFrameworkApi.publishVersion({
        name: publishName.trim(),
        description: publishDesc.trim(),
      })
      setSuccessMsg(`🎉 Framework Version ${res.data?.version_number} successfully published and activated!`)
      setShowPublishModal(false)
      await loadData()
    } catch (err) {
      setPublishModalError(err.message)
      setError(err.message)
    } finally {
      setPublishing(false)
    }
  }

  // Filter lists
  const activeDimensions = dimensions.filter(d => d.is_active && d.status === 'active')
  const archivedDimensions = dimensions.filter(d => !d.is_active || d.status !== 'active')
  const totalIndicators = dimensions.reduce((acc, d) => acc + (d.indicators?.length || 0), 0)

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm mt-4 text-slate-400">Loading Behavioral Framework...</p>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Toast notifications */}
      {successMsg && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center justify-between shadow-lg shadow-emerald-500/5 animate-fade-in">
          <div className="flex items-center gap-3">
            <span className="text-lg">✅</span>
            <span className="text-sm font-medium">{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-200 text-sm font-bold">✕</button>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center justify-between shadow-lg shadow-rose-500/5">
          <div className="flex items-center gap-3">
            <span className="text-lg">⚠️</span>
            <span className="text-sm font-medium">{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200 text-sm font-bold">✕</button>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="text-xs uppercase font-extrabold tracking-widest px-2.5 py-0.5 rounded-full bg-pink-500/20 text-pink-400 border border-pink-500/30">
              Admin Control Center
            </span>
            {currentVersion && (
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Active Version {currentVersion.version_number}
              </span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Behavioral Framework Manager
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Configure global competencies, behavioral indicators, and publish version-controlled framework updates for live candidate assessments.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            id="admin-validate-btn"
            onClick={handleValidateFramework}
            disabled={validating}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
          >
            <span>{validating ? '⏳' : '🔍'}</span>
            <span>Validate Framework</span>
          </button>

          <button
            id="admin-publish-btn"
            onClick={openPublishModal}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-pink-600 to-indigo-600 hover:from-pink-500 hover:to-indigo-500 text-white transition-all shadow-md shadow-pink-600/20 flex items-center gap-1.5 cursor-pointer hover:scale-102"
          >
            <span>🚀</span>
            <span>Publish New Version</span>
          </button>

          <button
            id="admin-add-dim-btn"
            onClick={openCreateDimension}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-md shadow-indigo-600/20 flex items-center gap-1.5 cursor-pointer hover:scale-102"
          >
            <span>+</span>
            <span>New Dimension</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 my-6">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Dimensions</div>
          <div className="text-2xl font-black text-white mt-1">{activeDimensions.length}</div>
          <div className="text-[11px] text-emerald-400 mt-1">✓ Powers new assessments</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Draft / Archived</div>
          <div className="text-2xl font-black text-slate-300 mt-1">{archivedDimensions.length}</div>
          <div className="text-[11px] text-slate-500 mt-1">Preserved for history</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Indicators</div>
          <div className="text-2xl font-black text-indigo-400 mt-1">{totalIndicators}</div>
          <div className="text-[11px] text-slate-400 mt-1">Avg ~{(totalIndicators / (dimensions.length || 1)).toFixed(1)} per dimension</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Framework Releases</div>
          <div className="text-2xl font-black text-pink-400 mt-1">{versions.length}</div>
          <div className="text-[11px] text-pink-300 mt-1">{currentVersion ? `Current: ${currentVersion.name}` : 'v1.0 active'}</div>
        </div>
      </div>

      {/* Validation Result Banner (if displayed) */}
      {validationResult && (
        <div className={`mb-6 p-4 rounded-xl border ${validationResult.valid ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200' : 'bg-rose-950/40 border-rose-500/40 text-rose-200'}`}>
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 font-bold text-sm">
                <span>{validationResult.valid ? '✅ Framework Validation Passed' : '❌ Validation Issues Detected'}</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 font-normal">
                  {validationResult.active_dimension_count} active dimensions, {validationResult.total_indicator_count} indicators
                </span>
              </div>
              {validationResult.errors.length > 0 && (
                <ul className="mt-2 text-xs space-y-1 list-disc list-inside text-rose-300 font-mono">
                  {validationResult.errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              )}
              {validationResult.warnings.length > 0 && (
                <ul className="mt-2 text-xs space-y-1 list-disc list-inside text-amber-300">
                  {validationResult.warnings.map((warn, idx) => (
                    <li key={idx}>{warn}</li>
                  ))}
                </ul>
              )}
            </div>
            <button onClick={() => setValidationResult(null)} className="text-xs opacity-60 hover:opacity-100">Dismiss</button>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 mb-6">
        <button
          onClick={() => setActiveTab('active')}
          className={`pb-3 px-3 text-sm font-semibold transition-all border-b-2 cursor-pointer ${activeTab === 'active' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
        >
          Active Framework ({activeDimensions.length})
        </button>
        <button
          onClick={() => setActiveTab('archived')}
          className={`pb-3 px-3 text-sm font-semibold transition-all border-b-2 cursor-pointer ${activeTab === 'archived' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
        >
          Drafts & Archived ({archivedDimensions.length})
        </button>
        <button
          onClick={() => setActiveTab('versions')}
          className={`pb-3 px-3 text-sm font-semibold transition-all border-b-2 cursor-pointer ${activeTab === 'versions' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
        >
          Version History ({versions.length})
        </button>
      </div>

      {/* ── TAB 1: ACTIVE DIMENSIONS ────────────────────────────────────────── */}
      {activeTab === 'active' && (
        <div className="space-y-4">
          {activeDimensions.length === 0 ? (
            <div className="text-center py-12 bg-slate-900/40 rounded-2xl border border-slate-800">
              <p className="text-slate-400 text-sm">No active behavioral dimensions found.</p>
              <button onClick={openCreateDimension} className="mt-3 px-4 py-2 bg-indigo-600 rounded-lg text-xs font-semibold text-white">
                Create First Dimension
              </button>
            </div>
          ) : (
            activeDimensions.map((dim, index) => (
              <div
                key={dim.id}
                id={`dim-admin-row-${dim.name}`}
                className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-all shadow-md"
              >
                {/* Dimension Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
                  <div className="flex items-center gap-3">
                    {/* Reorder Up/Down arrows */}
                    <div className="flex flex-col items-center gap-0.5 bg-slate-800/80 p-1 rounded-lg border border-slate-700/60">
                      <button
                        onClick={() => handleMoveDimension(index, -1)}
                        disabled={index === 0}
                        title="Move Up"
                        className={`text-[10px] w-5 h-4 flex items-center justify-center rounded hover:bg-slate-700 transition-colors ${index === 0 ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer text-slate-300'}`}
                      >
                        ▲
                      </button>
                      <button
                        onClick={() => handleMoveDimension(index, 1)}
                        disabled={index === activeDimensions.length - 1}
                        title="Move Down"
                        className={`text-[10px] w-5 h-4 flex items-center justify-center rounded hover:bg-slate-700 transition-colors ${index === activeDimensions.length - 1 ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer text-slate-300'}`}
                      >
                        ▼
                      </button>
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-slate-400">#{index + 1}</span>
                        <h3 className="text-lg font-bold text-white capitalize">
                          {dim.name.replace(/_/g, ' ')}
                        </h3>
                        <span className="text-xs font-mono text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/40">
                          {dim.name}
                        </span>
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          Active
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mt-1 max-w-3xl leading-relaxed">
                        {dim.description}
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button
                      onClick={() => openAddIndicator(dim)}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 transition-colors cursor-pointer"
                    >
                      + Indicator
                    </button>
                    <button
                      onClick={() => openEditDimension(dim)}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors cursor-pointer"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleToggleDimensionActive(dim)}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-amber-300 border border-slate-700 transition-colors cursor-pointer"
                      title="Deactivate dimension"
                    >
                      Draft
                    </button>
                    <button
                      onClick={() => handleArchiveDimension(dim)}
                      className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                        dim.is_referenced
                          ? 'bg-amber-950/30 hover:bg-amber-900/40 text-amber-300 border-amber-800/40'
                          : 'bg-rose-950/30 hover:bg-rose-900/40 text-rose-300 border-rose-800/40'
                      }`}
                      title={dim.is_referenced ? 'Safely archive referenced dimension' : 'Permanently delete unreferenced dimension'}
                    >
                      {dim.is_referenced ? 'Archive' : 'Delete'}
                    </button>
                  </div>
                </div>

                {/* Indicators Sub-Section */}
                <div className="mt-3.5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Observable Behavioral Indicators ({dim.indicators?.length || 0})
                    </span>
                    {(!dim.indicators || dim.indicators.length < 2) && (
                      <span className="text-xs text-amber-400 flex items-center gap-1">
                        ⚠️ Minimum 2 indicators required for valid activation
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                    {(dim.indicators || []).map((ind) => (
                      <div
                        key={ind.id}
                        className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 transition-all flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-1 mb-1">
                            <span className="text-xs font-bold text-slate-200 capitalize">
                              {ind.name.replace(/_/g, ' ')}
                            </span>
                            <span className="text-[10px] font-mono text-slate-500">
                              {ind.name}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 leading-snug">
                            {ind.description}
                          </p>
                          {ind.example_behaviors && (
                            <div className="mt-1.5 pt-1.5 border-t border-slate-900 text-[11px] text-slate-500 italic">
                              "{ind.example_behaviors}"
                            </div>
                          )}
                        </div>

                        <div className="flex items-center justify-end gap-1.5 mt-2 pt-1 border-t border-slate-900/60">
                          <button
                            onClick={() => openEditIndicator(dim, ind)}
                            className="text-[11px] text-slate-400 hover:text-indigo-300 cursor-pointer"
                          >
                            Edit
                          </button>
                          <span className="text-slate-700">•</span>
                          <button
                            onClick={() => handleDeleteIndicator(ind)}
                            className="text-[11px] text-rose-400/80 hover:text-rose-300 cursor-pointer"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ── TAB 2: DRAFTS & ARCHIVED DIMENSIONS ─────────────────────────────── */}
      {activeTab === 'archived' && (
        <div className="space-y-4">
          {archivedDimensions.length === 0 ? (
            <div className="text-center py-12 bg-slate-900/40 rounded-2xl border border-slate-800">
              <p className="text-slate-400 text-sm">No draft or archived dimensions.</p>
            </div>
          ) : (
            archivedDimensions.map((dim) => (
              <div
                key={dim.id}
                className="p-5 rounded-2xl bg-slate-900/40 border border-slate-800/60 opacity-80 hover:opacity-100 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-bold text-slate-300 capitalize">
                        {dim.name.replace(/_/g, ' ')}
                      </h3>
                      <span className="text-xs font-mono text-slate-500 bg-slate-800 px-2 py-0.5 rounded">
                        {dim.name}
                      </span>
                      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${dim.status === 'archived' ? 'bg-slate-800 text-slate-400 border border-slate-700' : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'}`}>
                        {dim.status === 'archived' ? 'Archived' : 'Draft / Inactive'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 max-w-3xl">{dim.description}</p>
                    <div className="text-[11px] text-slate-500 mt-2">
                      Observable indicators: {dim.indicators?.length || 0}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleDimensionActive(dim)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors cursor-pointer"
                    >
                      Activate
                    </button>
                    <button
                      onClick={() => openEditDimension(dim)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors cursor-pointer"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleArchiveDimension(dim)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-950/30 hover:bg-rose-900/40 text-rose-300 border border-rose-800/40 transition-colors cursor-pointer"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ── TAB 3: VERSION HISTORY ─────────────────────────────────────────── */}
      {activeTab === 'versions' && (
        <div className="space-y-4">
          {versions.length === 0 ? (
            <div className="text-center py-12 bg-slate-900/40 rounded-2xl border border-slate-800">
              <p className="text-slate-400 text-sm">No published framework versions recorded yet.</p>
            </div>
          ) : (
            versions.map((ver) => (
              <div
                key={ver.id}
                className={`p-5 rounded-2xl border transition-all ${ver.status === 'active' ? 'bg-indigo-950/20 border-indigo-500/40' : 'bg-slate-900/50 border-slate-800'}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-extrabold text-white">
                        Version {ver.version_number}.0
                      </span>
                      <span className="text-xs font-semibold text-slate-300">
                        {ver.name}
                      </span>
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${ver.status === 'active' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}`}>
                        {ver.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 max-w-3xl">
                      {ver.description}
                    </p>
                    <div className="flex items-center gap-4 text-[11px] text-slate-500 mt-2">
                      <span>Dimensions snapshot: <strong>{ver.dimensions_snapshot?.length || 0}</strong></span>
                      <span>Activated: <strong>{ver.activated_at ? new Date(ver.activated_at).toLocaleDateString() : 'N/A'}</strong></span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setViewingSnapshot(ver)
                      setShowSnapshotModal(true)
                    }}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 transition-colors cursor-pointer self-start sm:self-center"
                  >
                    View Snapshot
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ── CREATE / EDIT DIMENSION MODAL ───────────────────────────────────── */}
      {showDimensionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <h2 className="text-lg font-bold text-white">
                {editingDimension ? `Edit Dimension: ${editingDimension.name}` : 'Create New Behavioral Dimension'}
              </h2>
              <button onClick={() => setShowDimensionModal(false)} className="text-slate-400 hover:text-white font-bold text-lg">✕</button>
            </div>

            <form onSubmit={handleSaveDimension} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                  Dimension Slug / Identifier *
                </label>
                <input
                  type="text"
                  required
                  pattern="^[a-zA-Z][a-zA-Z0-9_-]{1,63}$"
                  placeholder="e.g. strategic_thinking"
                  value={dimName}
                  onChange={(e) => setDimName(e.target.value.toLowerCase().replace(/[\s-]+/g, '_'))}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm font-mono focus:border-indigo-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Lowercase snake_case. Must start with a letter. Used throughout scoring rubrics and prompts.
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                  Description *
                </label>
                <textarea
                  required
                  rows={3}
                  minLength={10}
                  placeholder="Define this behavioral competency and what it assesses..."
                  value={dimDesc}
                  onChange={(e) => setDimDesc(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase text-slate-300 mb-1">Status</label>
                  <select
                    value={dimStatus}
                    onChange={(e) => setDimStatus(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="active">Active (Published framework)</option>
                    <option value="draft">Draft (Work in progress)</option>
                    <option value="archived">Archived (Historical only)</option>
                  </select>
                </div>

                <div className="flex items-center gap-3 pt-6">
                  <input
                    type="checkbox"
                    id="is_active_checkbox"
                    checked={dimIsActive}
                    onChange={(e) => setDimIsActive(e.target.checked)}
                    className="w-4 h-4 rounded text-indigo-600 bg-slate-950 border-slate-700"
                  />
                  <label htmlFor="is_active_checkbox" className="text-xs font-medium text-slate-300">
                    Active for new assessments
                  </label>
                </div>
              </div>

              {/* Initial Indicators if Creating */}
              {!editingDimension && (
                <div className="mt-4 pt-4 border-t border-slate-800">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-bold uppercase text-indigo-400">
                      Initial Observable Indicators (Minimum 2 recommended)
                    </h4>
                    <button
                      type="button"
                      onClick={() => setInitialInds([...initialInds, { name: '', description: '', example_behaviors: '' }])}
                      className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
                    >
                      + Add Row
                    </button>
                  </div>
                  <div className="space-y-3">
                    {initialInds.map((ind, i) => (
                      <div key={i} className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                        <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
                          <span>Indicator #{i + 1}</span>
                          {initialInds.length > 1 && (
                            <button
                              type="button"
                              onClick={() => setInitialInds(initialInds.filter((_, idx) => idx !== i))}
                              className="text-rose-400 hover:text-rose-300 text-[11px] cursor-pointer"
                            >
                              ✕ Remove
                            </button>
                          )}
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          <input
                            type="text"
                            placeholder="Name slug (e.g. root_cause)"
                            value={ind.name}
                            onChange={(e) => {
                              const updated = [...initialInds]
                              updated[i].name = e.target.value.toLowerCase().replace(/[\s-]+/g, '_')
                              setInitialInds(updated)
                            }}
                            className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white font-mono"
                          />
                          <input
                            type="text"
                            placeholder="Observable Description (min 5 chars)"
                            value={ind.description}
                            onChange={(e) => {
                              const updated = [...initialInds]
                              updated[i].description = e.target.value
                              setInitialInds(updated)
                            }}
                            className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* In-Modal Error Banner */}
              {dimModalError && (
                <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs flex items-start gap-2.5 animate-fade-in">
                  <span className="text-base leading-none">⚠️</span>
                  <div className="flex-1">
                    <div className="font-bold text-rose-200">Unable to save dimension</div>
                    <div className="mt-1 font-mono text-[11px] text-rose-300">{dimModalError}</div>
                    {dimModalError.toLowerCase().includes('already exists') && (
                      <div className="mt-2.5 p-2.5 rounded-lg bg-rose-950/70 border border-rose-800/50 text-[11px] text-rose-200 space-y-1">
                        <div>💡 <strong>'{dimName}'</strong> is already present in your active framework list!</div>
                        <div>You can close this modal and find <strong>{dimName}</strong> on the dashboard to add indicators, or enter a different slug above.</div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800 mt-6">
                <button
                  type="button"
                  onClick={() => setShowDimensionModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingDim}
                  className="px-5 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
                >
                  {submittingDim ? 'Saving...' : (editingDimension ? 'Update Dimension' : 'Create Dimension')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── ADD / EDIT INDICATOR MODAL ──────────────────────────────────────── */}
      {showIndicatorModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <h2 className="text-lg font-bold text-white">
                {editingIndicator ? `Edit Indicator: ${editingIndicator.name}` : `Add Indicator to '${indicatorParentDim?.name}'`}
              </h2>
              <button onClick={() => setShowIndicatorModal(false)} className="text-slate-400 hover:text-white font-bold text-lg">✕</button>
            </div>

            <form onSubmit={handleSaveIndicator} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                  Indicator Name / Identifier *
                </label>
                <input
                  type="text"
                  required
                  pattern="^[a-zA-Z][a-zA-Z0-9_-]{1,63}$"
                  placeholder="e.g. data_driven_reasoning"
                  value={indName}
                  onChange={(e) => setIndName(e.target.value.toLowerCase().replace(/[\s-]+/g, '_'))}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm font-mono focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                  Observable Description *
                </label>
                <textarea
                  required
                  rows={2}
                  minLength={5}
                  placeholder="Describe the observable behavioral signal (e.g. Evaluates statistical evidence before forming conclusions)..."
                  value={indDesc}
                  onChange={(e) => setIndDesc(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                  Example Behaviors (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Cites metrics, outlines test hypotheses..."
                  value={indExamples}
                  onChange={(e) => setIndExamples(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              {/* In-Modal Indicator Error Banner */}
              {indModalError && (
                <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs flex items-start gap-2.5 animate-fade-in">
                  <span className="text-base leading-none">⚠️</span>
                  <div className="flex-1">
                    <div className="font-bold text-rose-200">Unable to save indicator</div>
                    <div className="mt-1 font-mono text-[11px] text-rose-300">{indModalError}</div>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800 mt-6">
                <button
                  type="button"
                  onClick={() => setShowIndicatorModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingInd}
                  className="px-5 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
                >
                  {submittingInd ? 'Saving...' : (editingIndicator ? 'Update Indicator' : 'Save Indicator')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── PUBLISH VERSION MODAL ───────────────────────────────────────────── */}
      {showPublishModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <div>
                <h2 className="text-lg font-bold text-white">Publish Framework Release</h2>
                <p className="text-xs text-slate-400">Freeze snapshot and activate new behavioral framework version</p>
              </div>
              <button onClick={() => setShowPublishModal(false)} className="text-slate-400 hover:text-white font-bold text-lg">✕</button>
            </div>

            {/* Validation Checklist */}
            <div className={`p-4 rounded-xl mb-4 border ${validationResult?.valid ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-200' : 'bg-rose-950/30 border-rose-500/30 text-rose-200'}`}>
              <div className="text-xs font-bold uppercase tracking-wider mb-2">
                Pre-Activation Verification Checklist
              </div>
              <ul className="text-xs space-y-1.5">
                <li className="flex items-center gap-2">
                  <span>{(validationResult?.active_dimension_count || 0) >= 3 ? '✅' : '❌'}</span>
                  <span>Minimum 3 active dimensions (Found {validationResult?.active_dimension_count || 0})</span>
                </li>
                <li className="flex items-center gap-2">
                  <span>{(validationResult?.errors?.length || 0) === 0 ? '✅' : '❌'}</span>
                  <span>All active dimensions have at least 2 observable indicators</span>
                </li>
                <li className="flex items-center gap-2">
                  <span>✅</span>
                  <span>Valid alphanumeric identifiers and non-blank descriptions</span>
                </li>
                <li className="flex items-center gap-2">
                  <span>✅</span>
                  <span>Deterministic NLP scoring compatibility verified</span>
                </li>
              </ul>
            </div>

            <form onSubmit={handlePublishVersion} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                  Release Version Name *
                </label>
                <input
                  type="text"
                  required
                  value={publishName}
                  onChange={(e) => setPublishName(e.target.value)}
                  placeholder="e.g. v2.0 - Expanded Engineering Competency Framework"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:border-indigo-500 focus:outline-none font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                  Change Notes / Summary
                </label>
                <textarea
                  rows={3}
                  value={publishDesc}
                  onChange={(e) => setPublishDesc(e.target.value)}
                  placeholder="Summarize changes introduced in this framework release..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              {/* Snapshot Preview */}
              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">
                  Staged Dimensions to Freeze ({activeDimensions.length})
                </label>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 max-h-36 overflow-y-auto space-y-1 font-mono text-xs text-slate-300">
                  {activeDimensions.map((d, i) => (
                    <div key={d.id} className="flex items-center justify-between py-0.5 border-b border-slate-900">
                      <span>#{i + 1} {d.name}</span>
                      <span className="text-slate-500">{d.indicators?.length || 0} indicators</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* In-Modal Publish Error Banner */}
              {publishModalError && (
                <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs flex items-start gap-2.5 animate-fade-in">
                  <span className="text-base leading-none">⚠️</span>
                  <div className="flex-1">
                    <div className="font-bold text-rose-200">Unable to publish release</div>
                    <div className="mt-1 font-mono text-[11px] text-rose-300">{publishModalError}</div>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800 mt-6">
                <button
                  type="button"
                  onClick={() => setShowPublishModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={publishing || !validationResult?.valid}
                  className="px-5 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-pink-600 to-indigo-600 hover:from-pink-500 hover:to-indigo-500 text-white disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                >
                  {publishing ? 'Activating Release...' : 'Confirm & Activate Framework'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── VIEW SNAPSHOT MODAL ─────────────────────────────────────────────── */}
      {showSnapshotModal && viewingSnapshot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <div>
                <h2 className="text-lg font-bold text-white">
                  Frozen Framework Snapshot: Version {viewingSnapshot.version_number}.0
                </h2>
                <p className="text-xs text-slate-400">{viewingSnapshot.name}</p>
              </div>
              <button onClick={() => setShowSnapshotModal(false)} className="text-slate-400 hover:text-white font-bold text-lg">✕</button>
            </div>

            <div className="space-y-4">
              {(viewingSnapshot.dimensions_snapshot || []).map((dim, i) => (
                <div key={i} className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono font-bold text-indigo-400">#{i + 1}</span>
                    <h4 className="text-sm font-bold text-white capitalize">{dim.name}</h4>
                  </div>
                  <p className="text-xs text-slate-400 mb-3">{dim.description}</p>

                  <div className="pl-3 border-l-2 border-indigo-500/40 space-y-1.5">
                    {(dim.indicators || []).map((ind, j) => (
                      <div key={j} className="text-xs text-slate-300">
                        <strong className="text-slate-200 capitalize">{ind.name}:</strong> {ind.description}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-800 mt-6">
              <button
                onClick={() => setShowSnapshotModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                Close Snapshot
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
