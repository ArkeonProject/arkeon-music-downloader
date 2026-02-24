import { useState, useEffect } from 'react';
import './index.css';

// Type definitions
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
  file_path: string | null;
  download_status: string;
  downloaded_at: string | null;
  created_at: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'sources' | 'tracks'>('dashboard');
  const [sources, setSources] = useState<Source[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [newSource, setNewSource] = useState({ name: '', url: '', type: 'playlist' });
  const [singleUrl, setSingleUrl] = useState('');

  // Dashboard stats
  const totalTracks = tracks.length;
  const completedTracks = tracks.filter(t => t.download_status === 'completed').length;
  const failedTracks = tracks.filter(t => t.download_status === 'failed').length;
  const activeSources = sources.filter(s => s.status === 'active').length;

  const fetchData = async () => {
    try {
      const [sourcesRes, tracksRes] = await Promise.all([
        fetch(`${API_URL}/sources`),
        fetch(`${API_URL}/tracks`)
      ]);
      const sourcesData = await sourcesRes.json();
      const tracksData = await tracksRes.json();

      setSources(sourcesData);
      setTracks(tracksData);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // 10s polling
    return () => clearInterval(interval);
  }, []);

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSource.name || !newSource.url) return;
    try {
      await fetch(`${API_URL}/sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSource)
      });
      setNewSource({ name: '', url: '', type: 'playlist' });
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleSource = async (id: number, currentStatus: string) => {
    try {
      const newStatus = currentStatus === 'active' ? 'paused' : 'active';
      await fetch(`${API_URL}/sources/${id}/status?status=${newStatus}`, { method: 'PUT' });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleDeleteSource = async (id: number) => {
    try {
      await fetch(`${API_URL}/sources/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleDownloadSingle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!singleUrl) return;
    try {
      await fetch(`${API_URL}/tracks/download-single`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: singleUrl })
      });
      setSingleUrl('');
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleDeleteTrack = async (id: number) => {
    try {
      await fetch(`${API_URL}/tracks/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (e) { console.error(e); }
  };

  return (
    <div className="app-container">
      <h1 className="title">Arkeon Music Watcher</h1>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '30px' }}>
        <button className="btn" onClick={() => setActiveTab('dashboard')} style={{ opacity: activeTab === 'dashboard' ? 1 : 0.6 }}>Dashboard</button>
        <button className="btn" onClick={() => setActiveTab('sources')} style={{ opacity: activeTab === 'sources' ? 1 : 0.6 }}>Fuentes / Artistas</button>
        <button className="btn" onClick={() => setActiveTab('tracks')} style={{ opacity: activeTab === 'tracks' ? 1 : 0.6 }}>Biblioteca (Canciones)</button>
      </div>

      {activeTab === 'dashboard' && (
        <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <div className="glass-panel">
            <h3 style={{ margin: '0 0 10px 0', color: 'var(--text-secondary)' }}>Canciones Totales</h3>
            <div style={{ fontSize: '3rem', fontWeight: 'bold' }}>{totalTracks}</div>
          </div>
          <div className="glass-panel">
            <h3 style={{ margin: '0 0 10px 0', color: 'var(--text-secondary)' }}>Descargadas</h3>
            <div style={{ fontSize: '3rem', fontWeight: 'bold', color: 'var(--success)' }}>{completedTracks}</div>
          </div>
          <div className="glass-panel">
            <h3 style={{ margin: '0 0 10px 0', color: 'var(--text-secondary)' }}>Fallidas</h3>
            <div style={{ fontSize: '3rem', fontWeight: 'bold', color: 'var(--danger)' }}>{failedTracks}</div>
          </div>
          <div className="glass-panel">
            <h3 style={{ margin: '0 0 10px 0', color: 'var(--text-secondary)' }}>Fuentes Activas</h3>
            <div style={{ fontSize: '3rem', fontWeight: 'bold', color: 'var(--accent)' }}>{activeSources} <span style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>/ {sources.length}</span></div>
          </div>
        </div>
      )}

      {activeTab === 'sources' && (
        <div className="animate-fade-in">
          <div className="glass-panel" style={{ marginBottom: '20px' }}>
            <h2 style={{ marginTop: 0 }}>Añadir Nueva Fuente</h2>
            <form onSubmit={handleAddSource} style={{ display: 'flex', gap: '10px' }}>
              <input placeholder="Nombre (ej. Bad Bunny)" value={newSource.name} onChange={e => setNewSource({ ...newSource, name: e.target.value })} required style={{ flex: 1 }} />
              <select value={newSource.type} onChange={e => setNewSource({ ...newSource, type: e.target.value })} style={{ width: 'auto' }}>
                <option value="playlist">Playlist</option>
                <option value="artist">Artista (Canal)</option>
              </select>
              <input placeholder="URL de YouTube" value={newSource.url} onChange={e => setNewSource({ ...newSource, url: e.target.value })} required style={{ flex: 2 }} />
              <button type="submit" className="btn">+ Añadir</button>
            </form>
          </div>

          <div className="glass-panel">
            <h2 style={{ marginTop: 0 }}>Fuentes Monitorizadas</h2>
            {sources.length === 0 ? <p>No hay fuentes configuradas.</p> : (
              <table>
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map(s => (
                    <tr key={s.id}>
                      <td><strong>{s.name}</strong><br /><a href={s.url} target="_blank" style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{s.url.substring(0, 40)}...</a></td>
                      <td style={{ textTransform: 'capitalize' }}>{s.type}</td>
                      <td>
                        <span className={`status-badge status-${s.status}`}>
                          {s.status}
                        </span>
                      </td>
                      <td style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn" style={{ padding: '6px 12px' }} onClick={() => handleToggleSource(s.id, s.status)}>
                          {s.status === 'active' ? 'Pausar' : 'Activar'}
                        </button>
                        <button className="btn btn-danger" style={{ padding: '6px 12px' }} onClick={() => handleDeleteSource(s.id)}>
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {activeTab === 'tracks' && (
        <div className="animate-fade-in">
          <div className="glass-panel" style={{ marginBottom: '20px' }}>
            <h2 style={{ marginTop: 0 }}>Descarga Rápida (1 sola canción)</h2>
            <form onSubmit={handleDownloadSingle} style={{ display: 'flex', gap: '10px' }}>
              <input placeholder="URL del vídeo de YouTube" value={singleUrl} onChange={e => setSingleUrl(e.target.value)} required style={{ flex: 1 }} />
              <button type="submit" className="btn">+ Enviar a descargar</button>
            </form>
          </div>

          <div className="glass-panel">
            <h2 style={{ marginTop: 0 }}>Biblioteca</h2>
            {tracks.length === 0 ? <p>No hay canciones registradas.</p> : (
              <table>
                <thead>
                  <tr>
                    <th>Título</th>
                    <th>Estado</th>
                    <th>Fecha</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {tracks.map(t => (
                    <tr key={t.id}>
                      <td><strong>{t.title}</strong></td>
                      <td>
                        <span className={`status-badge status-${t.download_status}`}>
                          {t.download_status}
                        </span>
                      </td>
                      <td>{new Date(t.created_at).toLocaleString()}</td>
                      <td>
                        <button className="btn btn-danger" style={{ padding: '6px 12px' }} onClick={() => handleDeleteTrack(t.id)}>
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
