class ConfigPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (this.parentNode) {
      this.populateCurrentUser();
    }
  }

  get hass() {
    return this._hass;
  }

  async connectedCallback() {
    this.innerHTML = `
      <style>
        :host {
          display: block;
          min-height: 100vh;
          background-color: var(--lovelace-background, var(--primary-background-color));
          color: var(--primary-text-color);
          font-family: var(--paper-font-body1_-_font-family, "Arial", sans-serif);
          transition: background-color 0.3s, color 0.3s;
          padding: 20px;
        }

        .dashboard-container {
          max-width: 1000px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .brand-logo {
          position: absolute;
          top: 0;
          right: 0;
        }

        .brand-logo img {
          max-width: 40px;
          height: auto;
          transition: opacity 0.2s;
        }

        .brand-logo img:hover {
          opacity: 0.8;
        }

        .header-section {
          display: flex;
          flex-wrap: wrap;
          gap: 24px;
          background: var(--card-background-color);
          padding: 24px;
          border-radius: 16px;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.1));
        }

        .profile-info {
          flex: 1;
          min-width: 250px;
          text-align: center;
          border-right: 1px solid var(--divider-color);
          padding-right: 24px;
        }

        @media (max-width: 600px) {
          .profile-info {
            border-right: none;
            border-bottom: 1px solid var(--divider-color);
            padding-right: 0;
            padding-bottom: 24px;
          }
        }

        .profile-info img {
          width: 80px;
          height: 80px;
          border-radius: 50%;
          margin-bottom: 12px;
          border: 2px solid var(--primary-color);
          background: var(--secondary-background-color);
        }

        .profile-info h2 {
          margin: 8px 0;
          font-size: 1.5rem;
        }

        .profile-info p {
          color: var(--secondary-text-color);
          font-size: 0.9rem;
          margin-bottom: 16px;
        }

        .controls {
          display: flex;
          justify-content: center;
          gap: 12px;
          margin-bottom: 16px;
        }

        .btn {
          padding: 8px 16px;
          border-radius: 8px;
          border: none;
          cursor: pointer;
          font-weight: 500;
          transition: opacity 0.2s, transform 0.1s;
        }

        .btn:active { transform: scale(0.98); }

        .btn-primary { background: var(--primary-color); color: white; }
        .btn-outline { background: transparent; border: 1px solid var(--primary-color); color: var(--primary-color); }

        .system-status {
          flex: 2;
          min-width: 300px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          position: relative;
        }

        .status-grid {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .status-item {
          padding: 12px 0;
          border-bottom: 1px solid var(--divider-color);
        }

        .status-item:last-child {
          border-bottom: none;
        }

        .status-item h4 { margin: 0 0 4px 0; color: var(--secondary-text-color); font-size: 0.8rem; text-transform: uppercase; }

        .status-item a {
          color: var(--primary-color);
          text-decoration: none;
          font-weight: 500;
          transition: color 0.2s;
        }

        .status-item a:hover {
          color: var(--accent-color);
          text-decoration: underline;
        }

        .nav-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 20px;
        }

        .tile {
          background-color: var(--card-background-color);
          border-radius: 12px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 32px;
          text-align: center;
          font-weight: bold;
          text-decoration: none;
          color: var(--primary-text-color);
          box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.1));
          transition: background-color 0.3s, box-shadow 0.3s, transform 0.2s;
        }

        .tile:hover {
          background-color: var(--secondary-background-color);
          box-shadow: var(--ha-card-box-shadow-hover, 0 4px 8px rgba(0,0,0,0.15));
          transform: translateY(-2px);
        }

        .tile ha-icon {
          --mdc-icon-size: 40px;
          margin-bottom: 12px;
          color: var(--orange);
        }

        .footer-links {
          text-align: center;
          padding: 20px;
          color: var(--secondary-text-color);
        }

        .footer-links a {
          color: var(--primary-color);
          text-decoration: none;
          margin: 0 12px;
        }
      </style>

      <div class="dashboard-container">
        <div class="header-section">
          <div class="profile-info">
            <div id="current-user">
              <img src="/local/effortlesshome/user.png" alt="Profile">
              <h2 id="user-name">Loading...</h2>
              <p id="ha-url">Connecting...</p>
            </div>
            <div class="controls">
              <button id="logout-btn" class="btn btn-outline">Logout</button>
              <button id="restart-btn" class="btn btn-primary">Restart</button>
            </div>
          </div>

          <div class="system-status">
             <div class="brand-logo">
               <a href="https://www.effortlesshome.co" target="_blank">
                 <img src="/local/effortlesshome/ehlogo.jpg" alt="EH Logo">
               </a>
             </div>
             <div class="status-grid">
                <div class="status-item">
                  <h4>Security</h4>
                  <a href="/profile/security">Two-Factor Authentication</a>
                </div>
                <div class="status-item">
                  <h4>Account</h4>
                  <a href="https://my.effortlesshome.co" target="_blank">Manage Subscription</a>
                </div>
             </div>
          </div>
        </div>

        <div class="nav-grid">
          ${this._tile("/effortlesshome-area-panel", "mdi:label-multiple", "Set Device Areas")}
          ${this._tile("/effortlesshome-label-panel", "mdi:label", "Set Labels")}
        </div>

        <div class="footer-links">
           <a href="https://effortlesshome.co" target="_blank">effortlesshome.co</a> |
           <a href="https://effortlesshome.co/support" target="_blank">Support</a>
        </div>
      </div>
    `;

    this.querySelector("#logout-btn")?.addEventListener("click", () => this.handleLogout());
    this.querySelector("#restart-btn")?.addEventListener("click", () => this.handleRestart());

    this.populateCurrentUser();
  }

  async handleLogout() {
    if (!this.hass) return;
    try {
      await this.hass.auth.revoke();
      if (window.localStorage) window.localStorage.clear();
      document.location.href = "/";
    } catch (err) {
      console.error(err);
      alert("Logout failed");
    }
  }

  async handleRestart() {
    if (!this.hass) return;
    if (!confirm("Are you sure you want to restart Home Assistant?")) return;
    try {
      await this.hass.callService("homeassistant", "restart");
      alert("Restarting System...");
    } catch (err) {
      console.error(err);
      alert("Restart failed.");
    }
  }

  populateCurrentUser() {
    if (!this.hass) return;
    const nameEl = this.querySelector("#user-name");
    const urlEl = this.querySelector("#ha-url");
    if (nameEl) nameEl.textContent = this.hass.user.name;
    if (urlEl) urlEl.textContent = this.hass.states["sensor.ha_url"]?.state || "Connected";

    if (!this.hass.user.is_admin) {
      const restartBtn = this.querySelector("#restart-btn");
      if (restartBtn) restartBtn.style.display = "none";
    }
  }

  _tile(href, icon, label) {
    return `
      <a href="${href}" class="tile">
        <ha-icon icon="${icon}"></ha-icon>
        ${label}
      </a>
    `;
  }
}

customElements.define("effortlesshome-config-panel", ConfigPanel);
