import { useState, useEffect } from 'react';
import './index.css';

interface Source {
  id: number;
  url: string;
  name: string;
  type: string;
  status: string;
  created_at: string;
}

interface Track {
  id: number;
  youtube_id: string;
  title: string;
  source_id: number | null;
  source_name: string | null;
  source_type: string | null;
  file_path: string | null;
  download_status: string;
  downloaded_at: string | null;
  created_at: string;
  published_at: string | null;
  artist: string | null;
}

const API = import.meta.env.VITE_API_URL || '/api';

function App() {
  const [sources, setSources] = useState<Source[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);

  const [totalTracks, setTotalTracks] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [availableArtists, setAvailableArtists] = useState<string[]>([]);
  const [availableYears, setAvailableYears] = useState<string[]>([]);

  // Add form
  const [addUrl, setAddUrl] = useState('');
  const [addType, setAddType] = useState('playlist');
  const [addName, setAddName] = useState('');
  const [adding, setAdding] = useState(false);

  // Filters & Pagination
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [artistFilter, setArtistFilter] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState<number | ''>('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // Modals
  const [deleteTarget, setDeleteTarget] = useState<Track | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  // Cookies
  const [hasCookies, setHasCookies] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Global Stats
  const [stats, setStats] = useState({ completed: 0, pending: 0, failed: 0, ignored: 0 });

  const fetchData = async () => {
    try {
      const queryParams = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (filter !== 'all') queryParams.append('status', filter);
      if (search) queryParams.append('search', search);
      if (artistFilter) queryParams.append('artist', artistFilter);
      if (yearFilter) queryParams.append('year', yearFilter);
      if (sourceFilter !== '') queryParams.append('source_id', sourceFilter.toString());

      const [s, t, a, y, c, st] = await Promise.all([
        fetch(`${API}/sources`).then(r => r.json()),
        fetch(`${API}/tracks?${queryParams.toString()}`).then(r => r.json()),
        fetch(`${API}/tracks/artists`).then(r => r.json()),
        fetch(`${API}/tracks/years`).then(r => r.json()),
        fetch(`${API}/config/cookies`).then(r => r.json()),
        fetch(`${API}/tracks/stats`).then(r => r.json()),
      ]);
      setSources(s);
      setTracks(t.items || []);
      setTotalTracks(t.total || 0);
      setTotalPages(t.pages || 1);
      setAvailableArtists(a || []);
      setAvailableYears(y || []);
      setHasCookies(c.exists);
      setStats(st || { completed: 0, pending: 0, failed: 0, ignored: 0 });
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [page, pageSize, filter, search, artistFilter, yearFilter, sourceFilter, sortBy, sortOrder]);

  // ─── Stats ──────────────────────────────────
  const activeSources = sources.filter(s => s.status === 'active').length;

  // ─── Filtered tracks ────────────────────────
  // The server now processes the filtering and pagination, so `tracks` already contains
  // the correctly filtered and paginated items.
  const filtered = tracks;

  // ─── Handlers ───────────────────────────────
  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addUrl.trim()) return;
    setAdding(true);

    try {
      if (addType === 'track') {
        await fetch(`${API}/tracks/download-single`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: addUrl })
        });
      } else {
        const name = addName.trim() || (addType === 'playlist' ? 'Mi Playlist' : 'Artista');
        await fetch(`${API}/sources`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: addUrl, name, type: addType })
        });
      }
      setAddUrl('');
      setAddName('');
      fetchData();
    } catch (e) { console.error(e); }
    setAdding(false);
  };

  const handleDelete = async (id: number) => {
    await fetch(`${API}/tracks/${id}`, { method: 'DELETE' });
    setDeleteTarget(null);
    fetchData();
  };

  const handleRestore = async (id: number) => {
    await fetch(`${API}/tracks/${id}/restore`, { method: 'PUT' });
    fetchData();
  };

  const handleCookieUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('file', e.target.files[0]);
    try {
      await fetch(`${API}/config/cookies`, { method: 'POST', body: fd });
      fetchData();
    } catch (err) { console.error(err); }
    setUploading(false);
    e.target.value = '';
  };

  const handleCookieDelete = async () => {
    await fetch(`${API}/config/cookies`, { method: 'DELETE' });
    fetchData();
  };

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
    setPage(1);
  };

  const SortIcon = ({ column }: { column: string }) => {
    if (sortBy !== column) return null;
    return <span className="sort-icon">{sortOrder === 'desc' ? '↓' : '↑'}</span>;
  };

  // ─── Badge label ────────────────────────────
  const badgeLabel = (s: string) =>
    s === 'completed' ? 'Descargada' :
      s === 'pending' ? 'Pendiente' :
        s === 'failed' ? 'Fallida' :
          s === 'ignored' ? 'Ignorada' : s;

  const formatDate = (d: string) => {
    const now = new Date();
    const date = new Date(d);
    const diffMs = now.getTime() - date.getTime();
    const diffH = diffMs / (1000 * 60 * 60);
    if (diffH < 1) return 'Hace unos min';
    if (diffH < 24) return `Hace ${Math.floor(diffH)}h`;
    if (diffH < 48) return 'Ayer';
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
  };

  return (
    <div className="app">
      {/* ─── Header ──────────────────────────── */}
      <header className="header">
        <span className="logo">Arkeon Music</span>
        <button className="settings-btn" onClick={() => setShowSettings(true)} title="Ajustes">
          ⚙
        </button>
      </header>

      {/* ─── Add Section ─────────────────────── */}
      <form className="card add-section" onSubmit={handleAdd}>
        <div className="add-row">
          <input
            className="add-input"
            placeholder="Pega la URL de YouTube aquí..."
            value={addUrl}
            onChange={e => setAddUrl(e.target.value)}
            required
          />
          {addType !== 'track' && (
            <input
              className="add-input"
              placeholder="Nombre (opcional)"
              value={addName}
              onChange={e => setAddName(e.target.value)}
              style={{ maxWidth: 180 }}
            />
          )}
          <select className="type-select" value={addType} onChange={e => setAddType(e.target.value)}>
            <option value="playlist">📋 Playlist</option>
            <option value="artist">🎤 Artista</option>
            <option value="track">🎵 Canción</option>
          </select>
          <button className="add-btn" type="submit" disabled={adding}>
            {adding ? '...' : 'Añadir'}
          </button>
        </div>
      </form>

      {/* ─── Stats Bar ───────────────────────── */}
      <div className="stats-bar">
        <div className="stat">🎵 <span className="stat-value">{stats.completed}</span> descargadas</div>
        <div className="stat">📡 <span className="stat-value">{activeSources}</span> fuentes</div>
        {stats.pending > 0 && <div className="stat">⏳ <span className="stat-value">{stats.pending}</span> pendientes</div>}
        {stats.failed > 0 && <div className="stat">❌ <span className="stat-value">{stats.failed}</span> fallidas</div>}
        {stats.ignored > 0 && <div className="stat">🚫 <span className="stat-value">{stats.ignored}</span> ignoradas</div>}
      </div>

      {/* ─── Toolbar ─────────────────────────── */}
      <div className="toolbar" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        <div style={{ display: 'flex', gap: '15px', justifyContent: 'space-between', alignItems: 'center' }}>
          <input
            className="search-input"
            placeholder="Buscar..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
          <div className="filter-chips">
            {[
              { key: 'all', label: 'Todas' },
              { key: 'completed', label: 'Descargadas' },
              { key: 'pending', label: 'Pendientes' },
              { key: 'failed', label: 'Fallidas' },
              { key: 'ignored', label: 'Ignoradas' },
            ].map(f => (
              <button
                key={f.key}
                className={`chip ${filter === f.key ? 'active' : ''}`}
                onClick={() => { setFilter(f.key); setPage(1); }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="advanced-filters" style={{ display: 'flex', gap: '10px', marginTop: '10px', flexWrap: 'wrap' }}>
          <select className="filter-select" value={artistFilter} onChange={e => { setArtistFilter(e.target.value); setPage(1); }}>
            <option value="">👤 Todos los Artistas</option>
            {availableArtists.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <select className="filter-select" value={yearFilter} onChange={e => { setYearFilter(e.target.value); setPage(1); }}>
            <option value="">📅 Todos los Años</option>
            {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <select className="filter-select" value={sourceFilter} onChange={e => { setSourceFilter(e.target.value ? Number(e.target.value) : ''); setPage(1); }}>
            <option value="">📋 Todas las Playlists</option>
            {sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>

          <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', marginLeft: 'auto', marginRight: '5px' }}>Por pág:</span>
          <select className="filter-select" value={pageSize} onChange={e => { setPageSize(Number(e.target.value)); setPage(1); }} style={{ padding: '8px' }}>
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </div>
      </div>

      {/* ─── Track List (Table) ──────────────── */}
      <div className="track-table-container">
        <table className="track-table">
          <thead>
            <tr>
              <th className="sortable" onClick={() => handleSort('title')}>
                Canción <SortIcon column="title" />
              </th>
              <th className="sortable" onClick={() => handleSort('source_id')} style={{ width: '160px' }}>
                Fuente <SortIcon column="source_id" />
              </th>
              <th style={{ width: '110px' }}>Estado</th>
              <th className="sortable" onClick={() => handleSort('downloaded_at')} style={{ width: '130px' }}>
                Descarga <SortIcon column="downloaded_at" />
              </th>
              <th className="sortable" onClick={() => handleSort('published_at')} style={{ width: '140px' }}>
                Salida Oficial <SortIcon column="published_at" />
              </th>
              <th style={{ width: '70px' }}></th>
            </tr>
          </thead>

          {filtered.length === 0 ? (
            <tbody>
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '40px' }}>
                  <div className="empty-state">
                    <div className="icon">🎶</div>
                    <p>{tracks.length === 0 ? 'Añade una playlist o canción para empezar' : 'Sin resultados'}</p>
                  </div>
                </td>
              </tr>
            </tbody>
          ) : (
            <tbody>
              {filtered.map(t => (
                <tr key={t.id}>
                  <td>
                    <div className="track-title">
                      <a href={`https://youtube.com/watch?v=${t.youtube_id}`} target="_blank" rel="noreferrer">
                        {t.title}
                      </a>
                      {t.artist && (
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                          <span style={{ marginRight: '8px' }}>👤 {t.artist}</span>
                        </div>
                      )}
                    </div>
                  </td>
                  <td>
                    <div className="track-source" title={t.source_name || ''}>{t.source_name || '—'}</div>
                  </td>
                  <td>
                    <span className={`badge badge-${t.download_status}`}>
                      {badgeLabel(t.download_status)}
                    </span>
                  </td>
                  <td>
                    <div className="track-date">{formatDate(t.created_at)}</div>
                  </td>
                  <td>
                    <div className="track-date">{t.published_at ? t.published_at : '—'}</div>
                  </td>
                  <td>
                    <div className="track-actions">
                      {t.download_status === 'ignored' || t.download_status === 'failed' ? (
                        <button className="icon-btn restore" onClick={() => handleRestore(t.id)} title={t.download_status === 'failed' ? 'Reintentar' : 'Restaurar'}>
                          ♻️
                        </button>
                      ) : (
                        <button className="icon-btn danger" onClick={() => setDeleteTarget(t)} title="Eliminar">
                          🗑
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          )}
        </table>
      </div>

      {/* ─── Pagination ──────────────────────── */}
      {totalPages > 1 && (
        <div className="pagination" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '15px', marginTop: '20px' }}>
          <button
            className="btn btn-secondary"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            &laquo; Anterior
          </button>
          <span>Página <strong style={{ color: 'var(--text-light)' }}>{page}</strong> de {totalPages} ({totalTracks} en total)</span>
          <button
            className="btn btn-secondary"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Siguiente &raquo;
          </button>
        </div>
      )}

      {/* ─── Delete Modal ────────────────────── */}
      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>¿Eliminar canción?</h3>
            <p>
              <strong>{deleteTarget.title}</strong><br />
              Se borrará el archivo y quedará ignorada para no volver a descargarse.
              Puedes restaurarla desde el filtro "Ignoradas".
            </p>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setDeleteTarget(null)}>Cancelar</button>
              <button className="btn btn-danger" onClick={() => handleDelete(deleteTarget.id)}>Eliminar</button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Settings Modal ──────────────────── */}
      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal settings-panel" onClick={e => e.stopPropagation()}>
            <h3>Autenticación YouTube</h3>
            <p>
              Sube tu <code>cookies.txt</code> para descargar contenido restringido y evitar bloqueos.
            </p>
            <div className="cookie-status">
              <div className="cookie-indicator">
                <div className={`cookie-dot ${hasCookies ? 'active' : 'inactive'}`} />
                {hasCookies ? 'Cookies activas' : 'Sin cookies'}
              </div>
              {hasCookies ? (
                <button className="btn btn-danger" onClick={handleCookieDelete} style={{ padding: '8px 16px' }}>
                  Eliminar
                </button>
              ) : (
                <div className="upload-wrapper">
                  <input type="file" accept=".txt" onChange={handleCookieUpload} disabled={uploading} />
                  <button className="btn btn-primary" style={{ padding: '8px 16px', pointerEvents: 'none' }}>
                    {uploading ? 'Subiendo...' : 'Subir cookies.txt'}
                  </button>
                </div>
              )}
            </div>

            <div style={{ marginTop: '20px' }}>
              <h3>Fuentes activas</h3>
              {sources.length === 0 ? (
                <p style={{ fontSize: '13px' }}>Sin fuentes registradas.</p>
              ) : (
                sources.map(s => (
                  <div key={s.id} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '10px 0', borderBottom: '1px solid rgba(55,65,81,0.3)', fontSize: '13px'
                  }}>
                    <div>
                      <strong>{s.name}</strong>
                      <span style={{ color: 'var(--text-muted)', marginLeft: '8px' }}>{s.type}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <button
                        className={`badge badge-${s.status === 'active' ? 'completed' : 'pending'}`}
                        onClick={async () => {
                          const newStatus = s.status === 'active' ? 'paused' : 'active';
                          await fetch(`${API}/sources/${s.id}/status?status=${newStatus}`, { method: 'PUT' });
                          fetchData();
                        }}
                        style={{ cursor: 'pointer', border: 'none' }}
                        title={s.status === 'active' ? 'Pausar' : 'Reanudar'}
                      >
                        {s.status === 'active' ? '⏸ Activa' : '▶ Pausada'}
                      </button>
                      <button className="icon-btn danger" onClick={async () => {
                        await fetch(`${API}/sources/${s.id}`, { method: 'DELETE' });
                        fetchData();
                      }} title="Eliminar fuente">✕</button>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="modal-actions" style={{ marginTop: '20px' }}>
              <button className="btn btn-secondary" onClick={() => setShowSettings(false)}>Cerrar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
