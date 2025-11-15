/**
 * Digikey Token Setup Panel
 * 
 * Provides UI for setting up Digikey OAuth tokens in the admin settings
 */

export function renderPanel(target, data) {
    if (!target) {
        console.error("No target provided to admin token panel");
        return;
    }

    // Get the base URL from the browser
    const baseUrl = window.location.origin;
    const clientId = data.context?.client_id || '';
    const redirectUri = `${baseUrl}/plugin/suppliercart/digikeytoken/`;
    const authUrl = `https://api.digikey.com/v1/oauth2/authorize?response_type=code&client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}`;

    const hasClientId = clientId && clientId !== '';
    const tokenStatus = data.context?.has_token ? 'Configured' : 'Not configured';
    const refreshTokenStatus = data.context?.has_refresh_token ? 'Configured' : 'Not configured';

    target.innerHTML = `
        <div class="digikey-token-setup">
            <style>
                .digikey-token-setup {
                    padding: 20px;
                }
                .token-setup-card {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                    background: #f9f9f9;
                }
                .setup-step {
                    margin-bottom: 15px;
                }
                .setup-step h4 {
                    margin-top: 0;
                    color: #333;
                }
                .status-badge {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                }
                .status-ok {
                    background: #d4edda;
                    color: #155724;
                }
                .status-warning {
                    background: #fff3cd;
                    color: #856404;
                }
                .info-box {
                    background: #e7f3ff;
                    border-left: 4px solid #2196F3;
                    padding: 15px;
                    margin: 15px 0;
                }
                .code-box {
                    background: #f5f5f5;
                    border: 1px solid #ddd;
                    padding: 10px;
                    border-radius: 4px;
                    font-family: monospace;
                    word-break: break-all;
                    margin: 10px 0;
                }
            </style>

            <h3>Digikey OAuth Token Setup</h3>

            <div class="token-setup-card">
                <h4>Current Status</h4>
                <p>
                    <strong>Client ID:</strong> 
                    ${hasClientId ? '<span class="status-badge status-ok">Configured</span>' : '<span class="status-badge status-warning">Not Set</span>'}
                </p>
                <p>
                    <strong>Access Token:</strong> 
                    <span class="status-badge ${data.context?.has_token ? 'status-ok' : 'status-warning'}">${tokenStatus}</span>
                </p>
                <p>
                    <strong>Refresh Token:</strong> 
                    <span class="status-badge ${data.context?.has_refresh_token ? 'status-ok' : 'status-warning'}">${refreshTokenStatus}</span>
                </p>
            </div>

            ${!hasClientId ? `
                <div class="info-box">
                    <strong>⚠️ Setup Required</strong>
                    <p>Please configure your Digikey Client ID and Client Secret in the plugin settings above before generating tokens.</p>
                </div>
            ` : `
                <div class="token-setup-card">
                    <div class="setup-step">
                        <h4>Step 1: Register Redirect URI</h4>
                        <p>Add this redirect URI to your Digikey API application at <a href="https://developer.digikey.com/" target="_blank">developer.digikey.com</a>:</p>
                        <div class="code-box">${redirectUri}</div>
                    </div>

                    <div class="setup-step">
                        <h4>Step 2: Generate OAuth Token</h4>
                        <p>Click the button below to authorize this InvenTree instance with Digikey. You'll be redirected to Digikey to log in and authorize access.</p>
                        <button class="btn btn-primary btn-lg" onclick="window.open('${authUrl}', 'digikey-auth', 'width=800,height=600')" style="margin-top: 10px;">
                            <span class="fas fa-key"></span> Generate Digikey Token
                        </button>
                        <p style="margin-top: 10px; font-size: 14px; color: #666;">
                            After authorization, the tokens will be automatically saved to your plugin settings.
                        </p>
                    </div>

                    <div class="info-box">
                        <strong>ℹ️ Note:</strong>
                        <p>Tokens expire after a period of time. If you get authentication errors when transferring POs, come back here and regenerate your token.</p>
                    </div>
                </div>
            `}
        </div>
    `;
}

