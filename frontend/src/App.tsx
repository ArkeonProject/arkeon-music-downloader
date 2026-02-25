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

  // Add form
  const [addUrl, setAddUrl] = useState('');
  const [addType, setAddType] = useState('playlist');
  const [addName, setAddName] = useState('');
  const [adding, setAdding] = useState(false);

  // Filters & Pagination
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [artistFilter, setArtistFilter] = useState('');
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
      if (sourceFilter !== '') queryParams.append('source_id', sourceFilter.toString());

      const [s, t, a, c] = await Promise.all([
        fetch(`${API}/sources`).then(r => r.json()),
        fetch(`${API}/tracks?${queryParams.toString()}`).then(r => r.json()),
        fetch(`${API}/tracks/artists`).then(r => r.json()),
        fetch(`${API}/config/cookies`).then(r => r.json()),
      ]);
      setSources(s);
      setTracks(t.items || []);
      setTotalTracks(t.total || 0);
      setTotalPages(t.pages || 1);
      setAvailableArtists(a || []);
      setHasCookies(c.exists);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [page, pageSize, filter, search, artistFilter, sourceFilter, sortBy, sortOrder]);

  // ─── Stats ──────────────────────────────────
  const completed = tracks.filter(t => t.download_status === 'completed').length;
  const pending = tracks.filter(t => t.download_status === 'pending').length;
  const failed = tracks.filter(t => t.download_status === 'failed').length;
  const ignored = tracks.filter(t => t.download_status === 'ignored').length;
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
        <div className="stat">🎵 <span className="stat-value">{completed}</span> descargadas</div>
        <div className="stat">📡 <span className="stat-value">{activeSources}</span> fuentes</div>
        {pending > 0 && <div className="stat">⏳ <span className="stat-value">{pending}</span> pendientes</div>}
        {failed > 0 && <div className="stat">❌ <span className="stat-value">{failed}</span> fallidas</div>}
        {ignored > 0 && <div className="stat">🚫 <span className="stat-value">{ignored}</span> ignoradas</div>}
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
          <select className="filter-select" value={sourceFilter} onChange={e => { setSourceFilter(e.target.value ? Number(e.target.value) : ''); setPage(1); }}>
            <option value="">📋 Todas las Playlists</option>
            {sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>

          <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', marginLeft: 'auto', marginRight: '5px' }}>Por pág:</span>
          <select className="filter-select" value={pageSize} onChange={e => { setPageSize(Number(e.target.value)); setPage(1); }} style={{ padding: '8px', marginRight: '10px' }}>
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>

          <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', marginRight: '5px' }}>Ordenar:</span>
          <select className="filter-select" value={sortBy} onChange={e => setSortBy(e.target.value)}>
            <option value="created_at">Fecha añadido</option>
            <option value="downloaded_at">Fecha descarga</option>
            <option value="published_at">Antigüedad (YouTube)</option>
          </select>
          <select className="filter-select" value={sortOrder} onChange={e => setSortOrder(e.target.value)} style={{ width: '130px' }}>
            <option value="desc">↓ Más reciente</option>
            <option value="asc">↑ Más antiguo</option>
          </select>
        </div>
      </div>

      {/* ─── Track List ──────────────────────── */}
      <div className="card track-list">
        <div className="track-header">
          <span>Título</span>
          <span>Fuente</span>
          <span>Estado</span>
          <span>Fecha</span>
          <span></span>
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="icon">🎶</div>
            <p>{tracks.length === 0 ? 'Añade una playlist o canción para empezar' : 'Sin resultados'}</p>
          </div>
        ) : (
          filtered.map(t => (
            <div className="track-row" key={t.id}>
              <div className="track-title">
                <a href={`https://youtube.com/watch?v=${t.youtube_id}`} target="_blank" rel="noreferrer">
                  {t.title}
                </a>
                {(t.artist || t.published_at) && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {t.artist && <span style={{ marginRight: '8px' }}>👤 {t.artist}</span>}
                    {t.published_at && <span>📅 {t.published_at}</span>}
                  </div>
                )}
              </div>
              <div className="track-source">{t.source_name || '—'}</div>
              <div>
                <span className={`badge badge-${t.download_status}`}>
                  {badgeLabel(t.download_status)}
                </span>
              </div>
              <div className="track-date">{formatDate(t.created_at)}</div>
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
            </div>
          ))
        )}
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
