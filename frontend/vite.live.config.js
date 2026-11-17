// Local-only override: :8000 is taken on groot, so proxy /api to :8101.
import base from './vite.config.js'
base.server.port = 3002 // :3000 is another groot service
base.server.proxy['/api'].target = 'http://127.0.0.1:8101'
export default base
