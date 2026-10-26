import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Inject custom Prism icon CSS
const style = document.createElement('style');
style.textContent = `
  .prism-icon {
    width: 32px;
    height: 32px;
    display: inline-block;
    background-image: url('data:image/svg+xml;charset=utf-8,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 283.5 283.5"%3E%3Cdefs%3E%3ClinearGradient id="PrismGrad" x1="-658.8" y1="591.8" x2="-645" y2="650.7" gradientTransform="translate(2252.9 -1860.3) scale(3.2)" gradientUnits="userSpaceOnUse"%3E%3Cstop offset="0" stop-color="%23ff8e05"/%3E%3Cstop offset=".2" stop-color="%23fb1414"/%3E%3Cstop offset=".5" stop-color="%23bb1afd"/%3E%3Cstop offset=".7" stop-color="%233a56ff"/%3E%3Cstop offset="1" stop-color="%2300daa9"/%3E%3C/linearGradient%3E%3C/defs%3E%3Cg%3E%3Cpath fill="url(%23PrismGrad)" d="M77.5,25v178.4l154.5-89.2L77.5,25ZM111.4,83.8l52.8,30.5-52.4,30.5-.3-60.9ZM161.3,165.7l-83.8,48.4,83.8,48.4v-96.7Z"/%3E%3Cpath fill="%23fff" fill-opacity=".1" d="M161.3,165.7l-23.2,57.2,23.2,39.6v-96.7Z"/%3E%3Cpath fill="%23fff" fill-opacity=".1" d="M77.5,25l33.9,58.7,52.8,30.5h67.8L77.5,25Z"/%3E%3Cpath fill="%23fff" fill-opacity=".2" d="M77.5,203.1l33.9-58.7v-60.6l-33.9-58.7v178.1Z"/%3E%3Cpath fill="%23fff" fill-opacity=".2" d="M161.3,262.4l-83.8-48.4,60.6,8.8,23.2,39.6Z"/%3E%3C/g%3E%3C/svg%3E');
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
  }

  .prism-config-backdrop {
    position: fixed;
    inset: 0;
    z-index: 10000;
    display: grid;
    place-items: center;
    padding: 20px;
    background: rgb(0 0 0 / 62%);
  }

  .prism-config-dialog {
    width: min(480px, 100%);
    border: 1px solid var(--border-color, #4a4a4a);
    border-radius: 8px;
    background: var(--comfy-menu-bg, #252525);
    box-shadow: 0 18px 48px rgb(0 0 0 / 42%);
    color: var(--input-text, #eee);
  }

  .prism-config-dialog header,
  .prism-config-dialog footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 14px 16px;
  }

  .prism-config-dialog header {
    border-bottom: 1px solid var(--border-color, #4a4a4a);
    font-size: 16px;
    font-weight: 600;
  }

  .prism-config-dialog main {
    padding: 16px;
  }

  .prism-config-actions {
    display: grid;
    gap: 8px;
  }

  .prism-config-dialog button {
    padding: 8px 12px;
    border: 1px solid var(--border-color, #555);
    border-radius: 4px;
    background: var(--comfy-input-bg, #333);
    color: inherit;
    cursor: pointer;
  }

  .prism-config-dialog button i {
    margin-right: 6px;
  }

  .prism-config-dialog button:hover:not(:disabled) {
    background: var(--comfy-input-bg-hover, #424242);
  }

  .prism-config-dialog .prism-config-primary {
    border-color: var(--primary-bg, #337ab7);
    background: var(--primary-bg, #337ab7);
  }

  .prism-config-status {
    min-height: 18px;
    margin-top: 10px;
    color: var(--error-text, #f08a8a);
    font-size: 12px;
  }

  .prism-config-download {
    margin-top: 12px;
    font-size: 12px;
  }
`;
document.head.appendChild(style);

class PrismWebSocketClient {
  constructor() {
    this.socket = null;
    this.reconnectInterval = 5000;
    this.isConnected = false;
    this.contextReady = false;
    this.projectBrowserRequestsSent = 0;
    this.failedReconnectAttempts = 0;
    this.reconnectCancelled = false;
    this.connectionInProgress = false;
    this.reconnectTimer = null;
    this.contextLaunchInProgress = false;
    this.contextStartPromise = null;
    this.lastContextLaunchTs = 0;
    this.contextLaunchCooldownMs = 10000;
    this.pendingCommands = [];
    this.prismPathPrompted = false;
    this.prismUnavailable = false;
    this.initializeConnection();
  }
  
  async initializeConnection() {
    if (this.reconnectCancelled) {
      return;
    }

    if (this.connectionInProgress || this.reconnectTimer) {
      return;
    }

    if (this.socket && [WebSocket.CONNECTING, WebSocket.OPEN].includes(this.socket.readyState)) {
      return;
    }

    this.connectionInProgress = true;

    // Connect directly to Prism Comfy context on port 8765.
    this.connect();
  }

  async getComfyUIRootFolder() {
    try {
      const response = await fetch('/prism/get_comfyui_root');
      if (!response.ok) {
        return "";
      }

      const data = await response.json();
      return data.comfyui_root || "";
    } catch (error) {
      console.warn("[Prism] Failed to query ComfyUI root folder:", error);
      return "";
    }
  }

  runPythonScript(pythonExecutable, scriptPath, scriptArgs = [], cwd = null) {
    if (this.contextStartPromise) return this.contextStartPromise;
    this.contextStartPromise = this.startPrismContext(pythonExecutable, scriptPath, scriptArgs, cwd)
      .finally(() => { this.contextStartPromise = null; });
    return this.contextStartPromise;
  }

  async waitForPrismContext(pid) {
    const deadline = Date.now() + 30000;
    this.startConnectionAttempt();
    while (Date.now() < deadline) {
      let response;
      let data;
      try {
        response = await fetch(`/prism/get_context_status?pid=${encodeURIComponent(pid)}`);
        data = await response.json();
      } catch (error) {
        throw new Error('Could not check Prism startup. Restart ComfyUI and try again.');
      }
      if (!response.ok || !data.success || !data.running) {
        throw new Error(data.error || 'Prism closed before it could connect. Check the ComfyUI console for details.');
      }
      if (this.contextReady && this.isConnected && this.socket?.readyState === WebSocket.OPEN) return true;
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    throw new Error('Prism did not finish initializing within 30 seconds. Check the ComfyUI console for details.');
  }

  async startPrismContext(pythonExecutable, scriptPath, scriptArgs = [], cwd = null) {
    this.reconnectCancelled = false;
    try {
      console.log('[Prism] Running Python script:', {
        pythonExecutable,
        scriptPath,
        scriptArgs,
        cwd
      });
      const response = await fetch('/prism/run_python_script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          python_executable: pythonExecutable,
          script_path: scriptPath,
          script_args: scriptArgs,
          cwd,
        })
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to run python script');
      }

      console.log('[Prism] Started Prism Comfy context process:', data);
      return await this.waitForPrismContext(data.pid);
    } catch (error) {
      console.warn('[Prism] Failed to start Prism Comfy context process:', error);
      this.reconnectCancelled = true;
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
      window.alert(`Prism could not start.\n\n${error.message || 'Check the ComfyUI console for details, then try again.'}`);
      return false;
    }
  }

  async configurePrismRoot() {
    return new Promise((resolve) => {
      const backdrop = document.createElement('div');
      backdrop.className = 'prism-config-backdrop';
      backdrop.innerHTML = `
        <section class="prism-config-dialog" role="dialog" aria-modal="true" aria-labelledby="prism-config-title">
          <header><span id="prism-config-title">Prism is not configured</span></header>
          <main>
            <div class="prism-config-actions" id="prism-config-actions">
              <button type="button" class="prism-config-primary" id="prism-config-download"><i class="pi pi-download" aria-hidden="true"></i>Download Prism</button>
              <button type="button" id="prism-config-browse"><i class="pi pi-folder-open" aria-hidden="true"></i>Find existing Prism</button>
              <button type="button" id="prism-config-help"><i class="pi pi-question-circle" aria-hidden="true"></i>Help</button>
            </div>
            <div class="prism-config-status" id="prism-config-status" role="alert" hidden></div>
          </main>
          <footer>
            <button type="button" id="prism-config-cancel"><i class="pi pi-times" aria-hidden="true"></i>Cancel</button>
          </footer>
        </section>`;
      document.body.appendChild(backdrop);

      const status = backdrop.querySelector('#prism-config-status');
      const actions = backdrop.querySelector('#prism-config-actions');
      const title = backdrop.querySelector('#prism-config-title');
      let setupId = null;
      let setupRunning = false;
      let closing = false;
      let closed = false;
      const setSetupRunning = (running) => {
        setupRunning = running;
        actions.hidden = running;
        actions.style.display = running ? 'none' : '';
        title.textContent = running ? 'Prism setup in progress' : 'Prism is not configured';
      };
      const cancelSetup = async () => {
        if (!setupId) return;
        const response = await fetch('/prism/cancel_prism_setup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ setup_id: setupId }),
          keepalive: true,
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
          throw new Error('Unable to stop setup. Check the ComfyUI console and try Cancel again.');
        }
      };
      const cancelOnPageHide = () => {
        if (!setupRunning || !setupId) return;
        closing = true;
        const body = new Blob([JSON.stringify({ setup_id: setupId })], { type: 'application/json' });
        if (!navigator.sendBeacon('/prism/cancel_prism_setup', body)) {
          void cancelSetup().catch((error) => console.warn('[Prism] Could not cancel setup:', error));
        }
      };
      const onKeyDown = (event) => {
        if (event.key === 'Escape') {
          event.preventDefault();
          void close(false);
        }
      };
      const finishClose = (configured) => {
        closed = true;
        window.removeEventListener('pagehide', cancelOnPageHide);
        document.removeEventListener('keydown', onKeyDown);
        backdrop.remove();
        resolve(configured);
      };
      const close = async (configured) => {
        if (closed || closing) return;
        closing = true;
        if (!configured && setupRunning) {
          status.textContent = 'Stopping Prism setup...';
          try {
            await cancelSetup();
          } catch (error) {
            closing = false;
            showError(error.message);
            return;
          }
        }
        finishClose(configured);
      };
      window.addEventListener('pagehide', cancelOnPageHide);
      document.addEventListener('keydown', onKeyDown);
      const showError = (message) => {
        status.style.color = 'var(--error-text, #f08a8a)';
        status.textContent = message;
        status.hidden = !message;
      };
      const waitForSetupCompletion = async (setupPid) => {
        for (let attempt = 0; attempt < 900 && !closed && !closing; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          if (closed || closing) return;
          const response = await fetch('/prism/complete_prism_setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pid: setupPid }),
          });
          const data = await response.json();
          if (closed || closing) return;
          console.info('[Prism] Download Prism: setup completion check.', { attempt, data });
          if (!response.ok || data.error) {
            throw new Error('Prism setup failed. Check the ComfyUI console and try again.');
          }
          if (data.cancelled) {
            setupRunning = false;
            finishClose(false);
            return;
          }
          if (!data.installed) {
            if (data.message) {
              status.textContent = data.message;
            }
            continue;
          }
          if (!response.ok || !data.success) {
            throw new Error('Prism could not be configured. Check the ComfyUI console and try again.');
          }
          setupRunning = false;
          setupId = null;
          status.textContent = 'Opening Prism Project Browser...';
          const browserRequestsBeforeStartup = this.projectBrowserRequestsSent;
          const started = await this.ensurePrismComfyContextRunning(true);
          if (closed || closing) return;
          if (!started) {
            throw new Error('Prism is installed but could not be opened. Check the ComfyUI console.');
          }
          this.openProjectBrowserAfterSetup(browserRequestsBeforeStartup);
          finishClose('started');
          return;
        }
        if (closed || closing) return;
        await cancelSetup();
        throw new Error('Prism setup took too long and was stopped. Check the ComfyUI console before retrying.');
      };

      backdrop.querySelector('#prism-config-cancel').addEventListener('click', () => close(false));
      backdrop.addEventListener('click', (event) => {
        if (event.target === backdrop) close(false);
      });
      backdrop.querySelector('#prism-config-browse').addEventListener('click', async () => {
        console.info('[Prism] Find existing Prism: opening folder picker.');
        try {
          const response = await fetch('/prism/browse_prism_root', { method: 'POST' });
          const responseText = await response.text();
          console.info('[Prism] Find existing Prism: picker response.', {
            status: response.status,
            ok: response.ok,
            body: responseText,
          });
          const data = JSON.parse(responseText);
          if (data.success && data.prism_root) {
            console.info('[Prism] Find existing Prism: saving selected path.', data.prism_root);
            const configureResponse = await fetch('/prism/configure_prism_root', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ prism_root: data.prism_root }),
            });
            const configureText = await configureResponse.text();
            console.info('[Prism] Find existing Prism: configuration response.', {
              status: configureResponse.status,
              ok: configureResponse.ok,
              body: configureText,
            });
            const configureData = JSON.parse(configureText);
            if (configureResponse.ok && configureData.success) {
              console.info('[Prism] Find existing Prism: configuration saved.');
              close(true);
            } else {
              console.warn('[Prism] Find existing Prism: configuration was rejected.', configureData);
              showError(configureData.error || 'The Prism installation path could not be saved.');
            }
          } else {
            console.info('[Prism] Find existing Prism: no folder was selected.', data);
            if (response.ok) {
              showError('No folder was selected.');
            } else {
              showError(data.error || 'Unable to open the folder browser.');
            }
          }
        } catch (error) {
          console.warn('[Prism] Failed to browse for Prism:', error);
          showError('Unable to configure Prism. See the browser console for details.');
        }
      });
      backdrop.querySelector('#prism-config-download').addEventListener('click', async () => {
        console.info('[Prism] Download Prism: requesting setup script.');
        const downloadButton = backdrop.querySelector('#prism-config-download');
        if (setupRunning || closed || closing) return;
        downloadButton.disabled = true;
        setupId = crypto.randomUUID?.() || Array.from(
          crypto.getRandomValues(new Uint8Array(16)),
          value => value.toString(16).padStart(2, '0'),
        ).join('');
        setSetupRunning(true);
        status.textContent = 'Preparing Prism setup...';
        status.style.color = 'var(--input-text, #eee)';
        status.hidden = false;
        try {
          const response = await fetch('/prism/download_prism_setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ setup_id: setupId }),
          });
          const responseText = await response.text();
          if (closed || closing) return;
          console.info('[Prism] Download Prism: setup response.', {
            status: response.status,
            ok: response.ok,
            body: responseText,
          });
          const data = JSON.parse(responseText);
          if (response.ok && data.success) {
            status.textContent = 'Downloading and installing Prism...';
            await waitForSetupCompletion(data.pid);
          } else {
            throw new Error('Unable to start Prism setup. Check your internet connection and try again.');
          }
        } catch (error) {
          console.warn('[Prism] Failed to download Prism:', error);
          if (closed || closing) return;
          if (setupRunning) {
            try {
              await cancelSetup();
            } catch (cancelError) {
              showError(cancelError.message);
              return;
            }
          }
          setSetupRunning(false);
          setupId = null;
          showError(error.message || 'Prism setup failed. Check the ComfyUI console and try again.');
        } finally {
          downloadButton.disabled = false;
        }
      });
      backdrop.querySelector('#prism-config-help').addEventListener('click', () => {
        window.open('https://prism-pipeline.com/docs/latest/plugins/comfyui/', '_blank', 'noopener,noreferrer');
      });
      backdrop.querySelector('#prism-config-download').focus();
    });
  }

  openProjectBrowserAfterSetup(previousRequests) {
    if (this.projectBrowserRequestsSent === previousRequests) {
      this.sendToDesktopApp({ action: 'open_project_browser' });
    }
  }

  async ensurePrismComfyContextRunning(force = false, promptForPrismPath = false) {
    if (this.isConnected && this.socket?.readyState === WebSocket.OPEN) {
      return this.contextReady || this.contextStartPromise || false;
    }
    if (this.reconnectCancelled && !force && !promptForPrismPath) return false;
    const now = Date.now();
    if (this.contextLaunchInProgress) {
      return this.contextStartPromise || false;
    }

    if (!force && !promptForPrismPath && now - this.lastContextLaunchTs < this.contextLaunchCooldownMs) {
      return false;
    }

    this.contextLaunchInProgress = true;
    this.lastContextLaunchTs = now;

    try {
      const response = await fetch('/prism/get_launch_config');
      const data = await response.json();
      if (!response.ok || !data.success) {
        this.prismUnavailable = Boolean(data.requires_prism_path);
        if (this.prismUnavailable && promptForPrismPath && !this.prismPathPrompted) {
          this.prismPathPrompted = true;
          this.contextLaunchInProgress = false;
          const configured = await this.configurePrismRoot();
          this.prismPathPrompted = false;
          if (configured === 'started') return true;
          if (configured) {
            this.prismUnavailable = false;
            this.lastContextLaunchTs = 0;
            return await this.ensurePrismComfyContextRunning(true);
          }
        }
        throw new Error(data.error || 'Failed to get Prism launch config');
      }

      this.prismUnavailable = false;
      return await this.runPythonScript(
        data.python_executable,
        data.script_path,
        data.script_args || [],
        data.cwd || null,
      );
    } catch (error) {
      console.warn('[Prism] Could not launch Prism Comfy context process:', error);
      return false;
    } finally {
      this.contextLaunchInProgress = false;
    }
  }

  scheduleReconnect(delayMs = this.reconnectInterval) {
    if (this.reconnectCancelled || this.reconnectTimer || this.prismUnavailable) {
      return;
    }

    if (!this.contextLaunchInProgress) this.failedReconnectAttempts += 1;
    if (!this.contextLaunchInProgress && this.failedReconnectAttempts >= 3) {
      const retry = window.confirm("ComfyUI could not connect to Prism. Do you want to retry?");
      if (!retry) {
        this.reconnectCancelled = true;
        console.log("[Prism] Reconnect cancelled by user");
        return;
      }

      this.failedReconnectAttempts = 0;
    }

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.initializeConnection();
    }, delayMs);
  }

  startConnectionAttempt() {
    if (this.connectionInProgress || this.reconnectTimer) {
      return;
    }

    this.reconnectCancelled = false;
    this.initializeConnection();
  }

  sendPendingCommands() {
    const commands = this.pendingCommands.splice(0);
    for (const command of commands) {
      this.sendToDesktopApp(command);
    }
  }
  
  connect() {
    try {
      console.log("[Prism] Connecting to ComfyUI context Prism (port 8765)...");
      this.socket = new WebSocket("ws://localhost:8765");
      
      this.socket.onopen = async () => {
        console.log("[Prism] Connected to ComfyUI context Prism");
        this.isConnected = true;
        this.contextReady = false;
        this.connectionInProgress = false;
        this.failedReconnectAttempts = 0;

        const comfyuiRoot = await this.getComfyUIRootFolder();
        this.sendToDesktopApp({
          action: "set_comfyui_root",
          comfyui_root: comfyuiRoot
        });
        this.sendToDesktopApp({ action: 'get_context_status' });
      };
      
      this.socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("[Prism] Received command from Desktop App:", data);
        this.handleCommand(data);
      };
      
      this.socket.onerror = (error) => {
        console.error("[Prism] WebSocket error:", error);
      };
      
      this.socket.onclose = () => {
        const wasConnected = this.isConnected;
        console.log("[Prism] Disconnected from ComfyUI context Prism. Reconnecting...");
        this.isConnected = false;
        this.contextReady = false;
        this.connectionInProgress = false;

        if (!wasConnected) {
          this.ensurePrismComfyContextRunning();
        }

        this.scheduleReconnect();
      };
      
    } catch (error) {
      console.error("[Prism] Failed to connect:", error);
      this.connectionInProgress = false;

      this.ensurePrismComfyContextRunning();
      this.scheduleReconnect();
    }
  }
  
  handleCommand(data) {
    const action = data.action;
    
    switch (action) {
      case "prism_context_ready":
        if (data.ready && !this.contextReady) {
          this.contextReady = true;
          this.sendPendingCommands();
        }
        break;
      case "create_node":
        this.createNode(data.node_type, data.position, data.widget_values);
        break;
      case "save_workflow":
        this.saveWorkflow(data.path);
        break;
      case "open_workflow":
        this.openWorkflow(data.path);
        break;
      case "load_image":
        this.loadImage(data.path);
        break;
      case "load_sequence":
        this.loadSequence(data.path);
        break;
      case "load_product":
        this.loadProduct(data.path);
        break;
      case "set_node_inputs":
        this.setNodeInputs(data.node_id, data.inputs);
        break;
      case "get_current_workflow_info":
        this.sendCurrentWorkflowInfo(data.request_id);
        break;
      case "info":
        break;
      default:
        console.warn(`[Prism] Unknown action: ${action}`);
    }
  }
  
  createNode(nodeType, position, widgetValues) {
    try {
      const node = LiteGraph.createNode(nodeType);
      if (node) {
        if (position) {
          node.pos = position;
        } else {
          // Center position
          const canvasCenter = app.canvas.ds.visible_area;
          node.pos = [
            (canvasCenter[0] + canvasCenter[2]) / 2 - 100,
            (canvasCenter[1] + canvasCenter[3]) / 2 - 50
          ];
        }
        app.graph.add(node);
        
        // Set widget values if provided
        if (widgetValues && node.widgets) {
          for (const [widgetName, value] of Object.entries(widgetValues)) {
            const widget = node.widgets.find(w => w.name === widgetName);
            if (widget) {
              widget.value = value;
            }
          }
        }
        
        console.log(`[Prism] Created node: ${nodeType}`);
        this.sendResponse({ status: "success", action: "create_node", node_type: nodeType });
      } else {
        console.error(`[Prism] Failed to create node: ${nodeType}`);
        this.sendResponse({ status: "error", action: "create_node", message: "Node creation failed" });
      }
    } catch (error) {
      console.error(`[Prism] Error creating node:`, error);
      this.sendResponse({ status: "error", action: "create_node", message: error.message });
    }
  }
  
  async saveWorkflow(path) {
    try {
      // Determine if this is an absolute path (e.g., D:/tmp/file.json or /tmp/file.json)
      const isAbsolutePath = /^[a-zA-Z]:[\/\\]|^[\/\\]/.test(path || '');
      
      // Get current graph data
      const graphData = app.graph.serialize();
      
      if (isAbsolutePath) {
        // Save to absolute path using custom backend endpoint
        console.log(`[Prism] Saving to absolute path: ${path}`);
        
        const response = await fetch('/prism/save_workflow_absolute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filepath: path,
            workflow: graphData
          })
        });
        
        const result = await response.json();
        
        if (!result.success) {
          throw new Error(result.error || 'Failed to save workflow');
        }
        
        console.log(`[Prism] Workflow saved to absolute path: ${result.filepath}`);
        this.sendResponse({ 
          status: "success", 
          action: "save_workflow", 
          path: result.filepath 
        });
        
      } else {
        // Save to ComfyUI's workflows directory with UI update
        const vueApp = document.querySelector('#vue-app')?.__vue_app__;
        if (!vueApp || !vueApp.config.globalProperties.$pinia) {
          throw new Error('Pinia not accessible');
        }
        
        const pinia = vueApp.config.globalProperties.$pinia;
        
        // Get the workflow store
        const workflowStore = pinia._s.get('workflow');
        if (!workflowStore) {
          throw new Error('Workflow store not accessible');
        }
        
        // Get the active workflow
        const activeWorkflow = workflowStore.activeWorkflow;
        if (!activeWorkflow) {
          throw new Error('No active workflow');
        }
        
        // Update the workflow's change tracker with current graph state
        if (activeWorkflow.changeTracker) {
          activeWorkflow.changeTracker.checkState();
        }
        
        // Determine the save path
        const savePath = path || 'prism_auto_save.json';
        
        // Ensure path starts with 'workflows/' for consistency
        const fullPath = savePath.startsWith('workflows/') 
          ? savePath 
          : `workflows/${savePath}`;
        
        // Rename the workflow to the new path (keeps same tab, updates UI)
        await workflowStore.renameWorkflow(activeWorkflow, fullPath);
        
        // Save the workflow to the backend
        await workflowStore.saveWorkflow(activeWorkflow);
        
        console.log(`[Prism] Workflow saved to: ${fullPath}`);
        
        // Show toast notification
        const toastStore = pinia._s.get('toast');
        if (toastStore) {
          toastStore.add({
            severity: 'success',
            summary: 'Workflow Saved',
            detail: `Saved to ${savePath}`,
            life: 3000
          });
        }
        
        this.sendResponse({ 
          status: "success", 
          action: "save_workflow", 
          path: fullPath 
        });
      }
      
    } catch (error) {
      console.error(`[Prism] Error saving workflow:`, error);
      this.sendResponse({ 
        status: "error", 
        action: "save_workflow", 
        message: error.message 
      });
    }
  }
  
  async openWorkflow(path) {
    try {
      // Determine if this is an absolute path
      const isAbsolutePath = /^[a-zA-Z]:[/\\]|^[/\\]/.test(path || '');
      
      let workflowJSON;
      let filename;
      
      if (isAbsolutePath) {
        // Load from absolute path using custom endpoint
        console.log(`[Prism] Loading from absolute path: ${path}`);
        
        const response = await fetch('/prism/load_workflow_absolute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filepath: path })
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'Failed to load workflow');
        }
        
        workflowJSON = await response.text();
        filename = path.split(/[/\\]/).pop();
        
      } else {
        // Load from ComfyUI's workflows directory
        const fullPath = path.startsWith('workflows/') ? path : `workflows/${path}`;
        console.log(`[Prism] Loading from workflows directory: ${fullPath}`);
        
        const response = await fetch(`/userdata/${encodeURIComponent(fullPath)}`);
        
        if (!response.ok) {
          throw new Error(`Failed to load workflow: ${response.statusText}`);
        }
        
        workflowJSON = await response.text();
        filename = path.split('/').pop();
      }
      
      // Create a File object from the workflow JSON
      const blob = new Blob([workflowJSON], { type: 'application/json' });
      const file = new File([blob], filename, { type: 'application/json' });
      
      // Use handleFile to load the workflow
      await app.handleFile(file);
      // Save the workflow to clear the "dirty" state in the UI
      try {
        const vueApp = document.querySelector('#vue-app')?.__vue_app__;
        if (vueApp && vueApp.config.globalProperties.$pinia) {
          const pinia = vueApp.config.globalProperties.$pinia;
          const workflowStore = pinia._s.get('workflow');
          
          if (workflowStore && workflowStore.activeWorkflow) {
            await workflowStore.saveWorkflow(workflowStore.activeWorkflow);
            console.log(`[Prism] Workflow saved after loading`);
          }
        }
      } catch (saveError) {
        console.warn(`[Prism] Could not save workflow after loading:`, saveError);
      }

      console.log(`[Prism] Workflow loaded: ${filename}`);
      this.sendResponse({ 
        status: "success", 
        action: "open_workflow",
        path: path 
      });
      
    } catch (error) {
      console.error(`[Prism] Error loading workflow:`, error);
      this.sendResponse({ 
        status: "error", 
        action: "warning", 
        message: error.message 
      });
    }
  }

  sendCurrentWorkflowInfo(requestId = null) {
    let workflowPath = "";
    let source = "";

    try {
      const vueApp = document.querySelector('#vue-app')?.__vue_app__;
      const pinia = vueApp?.config?.globalProperties?.$pinia;
      const workflowStore = pinia?._s?.get('workflow');
      const activeWorkflow = workflowStore?.activeWorkflow;

      if (activeWorkflow) {
        workflowPath =
          activeWorkflow.path ||
          activeWorkflow.fullPath ||
          activeWorkflow.filepath ||
          activeWorkflow.name ||
          "";
        source = activeWorkflow.path ? "path" : (activeWorkflow.fullPath ? "fullPath" : (activeWorkflow.filepath ? "filepath" : "name"));
      }
    } catch (error) {
      console.warn('[Prism] Failed to query active workflow info:', error);
    }

    this.sendResponse({
      status: "success",
      action: "current_workflow_info",
      request_id: requestId,
      path: workflowPath,
      source,
    });
  }

  setNodeInputs(nodeId, inputs) {
    try {
      const node = app.graph.getNodeById(nodeId);
      if (!node) {
        console.error(`[Prism] Node not found with id: ${nodeId}`);
        return;
      }
      for (const [inputName, value] of Object.entries(inputs)) {
        const widget = node.widgets?.find(w => w.name === inputName);
        if (widget) {
          widget.value = value;
        } else {
          console.warn(`[Prism] Widget '${inputName}' not found on node ${nodeId}`);
        }
      }
      app.graph.setDirtyCanvas(true);
      console.log(`[Prism] Set inputs on node ${nodeId}:`, inputs);
    } catch (error) {
      console.error(`[Prism] Error setting node inputs:`, error);
    }
  }

  getPathInfo(path) {
    const rawPath = typeof path === "string" ? path : "";
    const normalizedPath = rawPath.replace(/\\/g, "/").trim();
    const cleanPath = normalizedPath.replace(/\s*\[[^\]]+\]\s*$/, "");
    const basename = cleanPath.split("/").pop() || cleanPath;
    const extension = basename.includes(".") ? basename.split(".").pop().toLowerCase() : "";

    return {
      rawPath,
      normalizedPath,
      cleanPath,
      basename,
      extension,
    };
  }

  isVideoExtension(extension) {
    return ["mp4", "avi", "mov", "mkv", "webm", "gif", "m4v"].includes(extension);
  }

  isProductExtension(extension) {
    return ["gltf", "glb", "fbx", "obj", "usd", "usda", "usdc", "abc"].includes(extension);
  }

  createNodeAtCanvasCenter(nodeType) {
    const node = LiteGraph.createNode(nodeType);
    if (!node) {
      return null;
    }

    const canvasCenter = app.canvas.ds.visible_area;
    node.pos = [
      (canvasCenter[0] + canvasCenter[2]) / 2 - 100,
      (canvasCenter[1] + canvasCenter[3]) / 2 - 50
    ];
    app.graph.add(node);
    return node;
  }

  createFirstAvailableNode(nodeTypes) {
    for (const nodeType of nodeTypes) {
      const node = this.createNodeAtCanvasCenter(nodeType);
      if (node) {
        return { node, nodeType };
      }
    }

    return { node: null, nodeType: null };
  }

  setNodeWidgetValue(node, widgetNames, value, debugLabel) {
    if (!node?.widgets?.length) {
      return false;
    }

    const names = Array.isArray(widgetNames) ? widgetNames : [widgetNames];
    const widget = node.widgets.find(w => names.includes(w.name));
    if (!widget) {
      return false;
    }

    widget.value = value;
    if (typeof widget.callback === "function") {
      widget.callback(value);
    }

    if (node.properties && Object.prototype.hasOwnProperty.call(node.properties, widget.name)) {
      node.properties[widget.name] = value;
    }

    if (Array.isArray(node.widgets_values)) {
      const widgetIndex = node.widgets.findIndex(w => w === widget);
      if (widgetIndex >= 0) {
        node.widgets_values[widgetIndex] = value;
      }
    }

    console.log(`[Prism] Set ${debugLabel} widget '${widget.name}' to: ${value}`);
    return true;
  }

  async refreshInputOptions(path, node, widgetNames, contextLabel) {
    const names = Array.isArray(widgetNames) ? widgetNames : [widgetNames];
    const widget = node?.widgets?.find(w => names.includes(w.name));

    const getWidgetOptions = () => {
      const values = widget?.options?.values;
      if (Array.isArray(values)) {
        return values;
      }

      if (typeof values === "function") {
        try {
          const result = values.call(widget, node, widget);
          return Array.isArray(result) ? result : [];
        } catch (error) {
          console.debug(`[Prism][debug] ${contextLabel}: failed to evaluate widget values`, error);
        }
      }

      return [];
    };

    const debugFetchInputFiles = async (stage) => {
      try {
        const response = await fetch('/internal/files/input');
        if (!response.ok) {
          console.debug(`[Prism][debug] ${contextLabel} ${stage}: /internal/files/input failed`, {
            status: response.status,
            statusText: response.statusText,
          });
          return;
        }

        const files = await response.json();
        const fileList = Array.isArray(files) ? files : [];
        console.debug(`[Prism][debug] ${contextLabel} ${stage}: /internal/files/input snapshot`, {
          count: fileList.length,
          hasTarget: fileList.includes(path),
          sample: fileList.slice(0, 10),
        });
      } catch (error) {
        console.debug(`[Prism][debug] ${contextLabel} ${stage}: /internal/files/input request error`, error);
      }
    };

    const beforeOptions = getWidgetOptions();
    console.debug(`[Prism][debug] ${contextLabel} before input refresh`, {
      path,
      widgetOptionCount: beforeOptions.length,
      widgetHasTarget: beforeOptions.includes(path),
      widgetOptionSample: beforeOptions.slice(0, 10),
    });
    await debugFetchInputFiles("before updateInputs");

    const vueApp = document.querySelector('#vue-app')?.__vue_app__;
    console.debug(`[Prism][debug] ${contextLabel}:  vueApp: ${vueApp}`);
    const pinia = vueApp?.config?.globalProperties?.$pinia;
    const assetsStore = pinia?._s?.get('assets');
    if (assetsStore?.updateInputs) {
      const refreshStart = performance.now();
      console.debug(`[Prism][debug] ${contextLabel}: calling assetsStore.updateInputs()`);
      await assetsStore.updateInputs();
      const refreshMs = Math.round(performance.now() - refreshStart);
      const afterOptions = getWidgetOptions();
      console.debug(`[Prism][debug] ${contextLabel}: assetsStore.updateInputs() finished`, {
        durationMs: refreshMs,
        widgetOptionCount: afterOptions.length,
        widgetHasTarget: afterOptions.includes(path),
        widgetOptionSample: afterOptions.slice(0, 10),
      });
    } else {
      console.debug(`[Prism][debug] ${contextLabel}: assetsStore.updateInputs() not available`, {
        hasVueApp: !!vueApp,
        hasPinia: !!pinia,
        assetsStoreKeys: assetsStore ? Object.keys(assetsStore) : [],
      });
    }

    await debugFetchInputFiles("after updateInputs");
  }

  markNodeDirty(node) {
    if (typeof node?.setDirtyCanvas === "function") {
      node.setDirtyCanvas(true, true);
    }
    if (typeof node?.onResize === "function") {
      node.onResize(node.size);
    }
    app.graph.setDirtyCanvas(true, true);
  }

  async loadImage(path) {
    try {
      const pathInfo = this.getPathInfo(path);
      if (this.isVideoExtension(pathInfo.extension)) {
        await this.loadVideo(path);
        return;
      }
      if (pathInfo.extension === "exr") {
        await this.loadEXR(path);
        return;
      }

      if (this.isProductExtension(pathInfo.extension)) {
        await this.loadProduct(path);
        return;
      }

      const node = this.createNodeAtCanvasCenter("LoadImage");
      if (!node) {
        console.error(`[Prism] Failed to load image: ${path}`);
        this.sendResponse({ status: "error", action: "warning", message: "Node creation failed" });
        return;
      }

      await this.refreshInputOptions(path, node, ["image"], "loadImage");
      this.setNodeWidgetValue(node, ["image"], path, "image");
      this.markNodeDirty(node);

      console.log(`[Prism] Loaded image: ${pathInfo.basename}`);
      this.sendResponse({ status: "success", action: "info", path: path });
    } catch (error) {
      console.error(`[Prism] Error loading image:`, error);
      this.sendResponse({ status: "error", action: "warning", message: error.message });
    }
  }

  loadSequence(path) {
    const node = this.createNodeAtCanvasCenter("PrismLoadMedia");
    if (!node) {
      console.error(`[Prism] Failed to create a sequence loader for: ${path}`);
      this.sendResponse({ status: "error", action: "warning", message: "Sequence loader node creation failed" });
      return;
    }

    const wasSet = this.setNodeWidgetValue(node, ["filepath"], path, "sequence");
    if (!wasSet) {
      console.warn(`[Prism] Filepath widget not found on PrismLoadMedia for: ${path}`);
    }
    this.markNodeDirty(node);
    console.log(`[Prism] Loaded image sequence: ${path}`);
    this.sendResponse({ status: "success", action: "info", path });
  }

  async loadVideo(path) {
    try {
      const pathInfo = this.getPathInfo(path);
      const { node, nodeType } = this.createFirstAvailableNode(["LoadVideo"]);
      if (!node) {
        console.error(`[Prism] Failed to load video: ${path}`);
        this.sendResponse({ status: "error", action: "warning", message: "Video node creation failed" });
        return;
      }

      await this.refreshInputOptions(path, node, ["video", "image", "file", "filename"], "loadVideo");
      const wasSet = this.setNodeWidgetValue(node, ["video", "image", "file", "filename", "path"], path, "video");
      if (!wasSet) {
        console.warn(`[Prism] Video widget not found on ${nodeType}`);
      }

      this.markNodeDirty(node);
      console.log(`[Prism] Loaded video with ${nodeType}: ${pathInfo.basename}`);
      this.sendResponse({ status: "success", action: "info", path: path });
    } catch (error) {
      console.error(`[Prism] Error loading video:`, error);
      this.sendResponse({ status: "error", action: "warning", message: error.message });
    }
  }

  async loadEXR(path) {
    try {
      const pathInfo = this.getPathInfo(path);
      const { node, nodeType } = this.createFirstAvailableNode(["◎ RadianceDigitalCinemaRead", "LoadEXR", "LoadExr", "LoadImage"]);
      if (!node) {
        console.error(`[Prism] Failed to load EXR: ${path}`);
        this.sendResponse({ status: "error", action: "warning", message: "EXR node creation failed" });
        return;
      }

      const isRadianceReadNode = nodeType === "◎ RadianceDigitalCinemaRead";
      const refreshWidgetNames = isRadianceReadNode
        ? ["source_path", "image", "exr", "file", "filename"]
        : ["image", "exr", "file", "filename"];
      const setWidgetNames = isRadianceReadNode
        ? ["source_path", "image", "exr", "file", "filename", "path"]
        : ["image", "exr", "file", "filename", "path"];

      await this.refreshInputOptions(path, node, refreshWidgetNames, "loadEXR");
      const wasSet = this.setNodeWidgetValue(node, setWidgetNames, path, "exr");
      if (!wasSet) {
        console.warn(`[Prism] EXR widget not found on ${nodeType}`);
      }

      this.markNodeDirty(node);
      console.log(`[Prism] Loaded EXR with ${nodeType}: ${pathInfo.basename}`);
      this.sendResponse({ status: "success", action: "info", path: path });
    } catch (error) {
      console.error(`[Prism] Error loading EXR:`, error);
      this.sendResponse({ status: "error", action: "warning", message: error.message });
    }
  }

  async loadProduct(path) {
    try {
      const pathInfo = this.getPathInfo(path);
      const { node, nodeType } = this.createFirstAvailableNode(["Load3D", "Load3d", "LoadModel"]);
      if (!node) {
        console.error(`[Prism] Failed to load 3D asset: ${path}`);
        this.sendResponse({ status: "error", action: "warning", message: "3D node creation failed" });
        return;
      }

      await this.refreshInputOptions(path, node, ["model_file", "model", "file", "path"], "loadProduct");
      const wasSet = this.setNodeWidgetValue(node, ["model_file", "model", "file", "path", "filename"], path, "3D model");
      if (!wasSet) {
        console.warn(`[Prism] 3D model widget not found on ${nodeType}`);
      }

      this.markNodeDirty(node);
      console.log(`[Prism] Loaded 3D asset with ${nodeType}: ${pathInfo.basename}`);
      this.sendResponse({ status: "success", action: "info", path: path });
    } catch (error) {
      console.error(`[Prism] Error loading 3D asset:`, error);
      this.sendResponse({ status: "error", action: "warning", message: error.message });
    }
  }
  
  sendToDesktopApp(command) {
    const socketOpen = this.socket && this.socket.readyState === WebSocket.OPEN;
    const startupCommand = ['set_comfyui_root', 'get_context_status'].includes(command.action);
    if (socketOpen && (this.contextReady || startupCommand)) {
      this.socket.send(JSON.stringify(command));
      if (command.action === 'open_project_browser') this.projectBrowserRequestsSent += 1;
      console.log("[Prism] Sent to Desktop App:", command);
    } else {
      console.log("[Prism] Waiting for Desktop App initialization");
      if (command.action !== 'open_project_browser'
          || !this.pendingCommands.some(pending => pending.action === 'open_project_browser')) {
        this.pendingCommands.push(command);
      }
      if (socketOpen) return;
      this.ensurePrismComfyContextRunning(false, true);
      this.startConnectionAttempt();
    }
  }
  
  sendResponse(response) {
    this.sendToDesktopApp(response);
  }
}

// Create global WebSocket client instance
let prismWS = null;

api.addEventListener("prism_missing_configuration", async () => {
  if (!prismWS || prismWS.prismPathPrompted) {
    return;
  }

  prismWS.prismPathPrompted = true;
  const configured = await prismWS.configurePrismRoot();
  prismWS.prismPathPrompted = false;
  if (configured && configured !== 'started') {
    prismWS.lastContextLaunchTs = 0;
    prismWS.ensurePrismComfyContextRunning(true);
  }
});

app.registerExtension({
  name: "PrismPipeline",
  
  async setup() {
    // Initialize WebSocket connection to desktop app
    prismWS = new PrismWebSocketClient();
    console.log("[Prism] Extension initialized");
  },
  
  commands: [
    { 
      id: "openProjectBrowser", 
      label: "Open Project Browser", 
      function: () => {
        if (prismWS) {
          prismWS.sendToDesktopApp({
            action: "open_project_browser"
          });
        }
      } 
    }
  ],
  
  menuCommands: [
    { 
      path: ["Prism"], 
      commands: ["openProjectBrowser"] 
    }
  ]
});

app.extensionManager.registerSidebarTab({
  id: "prismSidebarTab",
  icon: "prism-icon",
  title: "Prism",
  tooltip: "Prism Pipeline Tools",
  type: "custom",
  render: (el) => {
    el.innerHTML = `
      <div style="
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 24px;
        height: 100%;
      ">
        <div style="
          display: flex;
          justify-content: center;
          padding: 10px 0;
        ">
          <img 
            src="extensions/prism_pipeline/prisim-pipeline-logo_font_white.png"
            alt="Prism Pipeline"
            style="
              max-width: 70%;
              height: auto;
            "
          />
        </div>
        
        <div style="
          display: flex;
          flex-direction: column;
          gap: 10px;
        ">
          <button 
            id="prism-save-version"
            style="
              width: 100%;
              padding: 10px 16px;
              background-color: #2d2d2d;
              color: #ffffff;
              border: 1px solid #404040;
              border-radius: 6px;
              cursor: pointer;
              font-size: 13px;
              font-weight: 500;
              transition: all 0.2s ease;
            "
            onmouseover="this.style.backgroundColor='#3a3a3a'; this.style.borderColor='#505050';"
            onmouseout="this.style.backgroundColor='#2d2d2d'; this.style.borderColor='#404040';"
          >
            Save Version
          </button>

          <button
            id="prism-save-comment"
            style="
              width: 100%;
              padding: 10px 16px;
              background-color: #2d2d2d;
              color: #ffffff;
              border: 1px solid #404040;
              border-radius: 6px;
              cursor: pointer;
              font-size: 13px;
              font-weight: 500;
              transition: all 0.2s ease;
            "
            onmouseover="this.style.backgroundColor='#3a3a3a'; this.style.borderColor='#505050';"
            onmouseout="this.style.backgroundColor='#2d2d2d'; this.style.borderColor='#404040';"
          >
            Save with Comment
          </button>
          
          <button 
            id="prism-open-project-browser"
            style="
              width: 100%;
              padding: 10px 16px;
              background-color: #2d2d2d;
              color: #ffffff;
              border: 1px solid #404040;
              border-radius: 6px;
              cursor: pointer;
              font-size: 13px;
              font-weight: 500;
              transition: all 0.2s ease;
            "
            onmouseover="this.style.backgroundColor='#3a3a3a'; this.style.borderColor='#505050';"
            onmouseout="this.style.backgroundColor='#2d2d2d'; this.style.borderColor='#404040';"
          >
            Project Browser
          </button>
          
          <button 
            id="prism-settings"
            style="
              width: 100%;
              padding: 10px 16px;
              background-color: #2d2d2d;
              color: #ffffff;
              border: 1px solid #404040;
              border-radius: 6px;
              cursor: pointer;
              font-size: 13px;
              font-weight: 500;
              transition: all 0.2s ease;
            "
            onmouseover="this.style.backgroundColor='#3a3a3a'; this.style.borderColor='#505050';"
            onmouseout="this.style.backgroundColor='#2d2d2d'; this.style.borderColor='#404040';"
          >
            Settings
          </button>
        </div>
      </div>
    `;
    
    // Add click handlers
    const projectBrowserBtn = el.querySelector('#prism-open-project-browser');
    projectBrowserBtn.addEventListener('click', () => {
      if (prismWS) {
        prismWS.sendToDesktopApp({
          action: "open_project_browser"
        });
        console.log('[Prism] Sent open_project_browser command to Desktop App');
      } else {
        console.warn('[Prism] WebSocket not initialized');
      }
    });
    
    const saveVersionBtn = el.querySelector('#prism-save-version');
    saveVersionBtn.addEventListener('click', () => {
      if (prismWS) {
        prismWS.sendToDesktopApp({
          action: "save_version"
        });
        console.log('[Prism] Sent save_version command to Desktop App');
      } else {
        console.warn('[Prism] WebSocket not initialized');
      }
    });

    const saveCommentBtn = el.querySelector('#prism-save-comment');
    saveCommentBtn.addEventListener('click', () => {
      if (prismWS) {
        prismWS.sendToDesktopApp({
          action: "save_with_comment"
        });
        console.log('[Prism] Sent save_with_comment command to Desktop App');
      } else {
        console.warn('[Prism] WebSocket not initialized');
      }
    });
    
    const settingsBtn = el.querySelector('#prism-settings');
    settingsBtn.addEventListener('click', () => {
      if (prismWS) {
        prismWS.sendToDesktopApp({
          action: "open_settings"
        });
        console.log('[Prism] Sent open_settings command to Desktop App');
      } else {
        console.warn('[Prism] WebSocket not initialized');
      }
    });
  }
});

// Export for use in other modules if needed
export { prismWS };

app.registerExtension({
    name: "PrismButtonNode", async beforeRegisterNodeDef(nodeType, nodeData) {
        const isLoadNode = nodeData.name === "PrismLoadMedia";
        const isSaveNode = nodeData.name === "PrismSaveMedia";
        if (isLoadNode || isSaveNode) {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.call(this);
                }
                const node = this;
                const buttonLabel = isLoadNode ? "Select Version..." : "Select Entity...";
                const actionName = isLoadNode ? "select_version" : "select_entity";
                this.addWidget(
                    "button",
                    buttonLabel,
                    null,
                    () => {
                      if (prismWS) {
                        prismWS.sendToDesktopApp({
                          action: actionName,
                          node_name: node.title,
                          node_type: node.type,
                          node_id: node.id
                        });
                        console.log(`[Prism] Sent ${actionName} command to Desktop App for node:`, node.title);
                      } else {
                        console.warn('[Prism] WebSocket not initialized');
                      }
                    }, {
                        width: 150
                    }
                );
            };
        }
    },
});