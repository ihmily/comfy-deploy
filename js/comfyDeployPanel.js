import { app } from "../../../scripts/app.js";

let deployDialog;
const DEFAULT_CONFIG = {
    endpoint: "http://127.0.0.1:8080",
    apiKey: "",
};

// Global config object
let deployConfig = {...DEFAULT_CONFIG};

function loadConfig() {
    try {
        const savedEndpoint = localStorage.getItem('comfy_api_deploy_endpoint');
        const savedApiKey = localStorage.getItem('comfy_api_deploy_api_key');
        
        if (savedEndpoint) {
            deployConfig.endpoint = savedEndpoint;
        }
        
        if (savedApiKey) {
            deployConfig.apiKey = savedApiKey;
        }
        
        console.log("comfy-deploy: Config loaded");
    } catch (error) {
        console.error("comfy-deploy: Failed to load config", error);
    }
}

function saveConfig(config) {
    try {
        localStorage.setItem('comfy_api_deploy_endpoint', config.endpoint);
        localStorage.setItem('comfy_api_deploy_api_key', config.apiKey);
        
        // Update global config object
        deployConfig = {...config};
        
        console.log("comfy-deploy: Config saved");
        return true;
    } catch (error) {
        console.error("comfy-deploy: Failed to save config", error);
        return false;
    }
}

function getUILanguage() {
    try {
        const locale = app.ui.settings.getSettingValue('Comfy.Locale');
        return locale && locale.toLowerCase().startsWith('zh') ? 'zh' : 'en';
    } catch (e) {
        console.log('comfy-deploy: Failed to get UI language', e);
        return 'en';
    }
}

const i18n = {
    deployDialogTitle: {
        en: 'Comfy Deploy',
        zh: 'Comfy Deploy'
    },
    deployDescription: {
        en: 'Deploy the current workflow to ComfyDeploy, making it accessible via API. A new workflow version will be created after deployment.',
        zh: '将当前工作流部署到ComfyDeploy，使其可通过API进行访问和运行。部署后将创建一个新的工作流版本。'
    },
    deployNodeInfo: {
        en: 'Deployment will automatically add or update workflow nodes',
        zh: '部署会自动添加或更新工作流节点'
    },
    deployButton: {
        en: 'Deploy Workflow',
        zh: '部署工作流'
    },
    configOptions: {
        en: 'Configuration Options',
        zh: '配置选项'
    },
    configApiButton: {
        en: 'Configure API Endpoint & Key',
        zh: '配置 API 端点与密钥'
    },
    statusReady: {
        en: 'ComfyDeploy Ready',
        zh: 'ComfyDeploy 已就绪'
    },
    statusConnected: {
        en: 'ComfyDeploy Connected',
        zh: 'ComfyDeploy 已连接'
    },
    statusFailed: {
        en: 'Connection Failed',
        zh: '连接失败'
    },
    configRequired: {
        en: 'Please configure API endpoint and key',
        zh: '请配置 API 端点和密钥'
    },
    docs: {
        en: 'Docs',
        zh: '文档'
    },
    // Input dialog related text
    enterWorkflowName: {
        en: 'Enter Workflow Name',
        zh: '请输入工作流名称'
    },
    inputWorkflowName: {
        en: 'Input workflow name',
        zh: '输入工作流名称'
    },
    // Confirm dialog related text
    confirmDeploy: {
        en: 'Confirm Deployment',
        zh: '确认部署'
    },
    createNewVersion: {
        en: 'Will create a new version of workflow',
        zh: '将创建工作流的新版本'
    },
    workflowId: {
        en: 'Workflow ID',
        zh: '工作流ID'
    },
    currentVersion: {
        en: 'Current Version',
        zh: '当前版本'
    },
    createNewWorkflow: {
        en: 'Will create new workflow',
        zh: '将创建新工作流'
    },
    // Config dialog related text
    configTitle: {
        en: 'Comfy Deploy Config',
        zh: 'Comfy Deploy 配置'
    },
    endpointLabel: {
        en: 'Endpoint',
        zh: 'API端点'
    },
    apiKeyLabel: {
        en: 'API Key',
        zh: 'API 密钥'
    },
    endpointPlaceholder: {
        en: 'Example: http://127.0.0.1:8080',
        zh: '例如: http://127.0.0.1:8080'
    },
    apiKeyPlaceholder: {
        en: 'API Key',
        zh: 'API 密钥'
    },
    save: {
        en: 'Save',
        zh: '保存'
    },
    // Button text
    cancel: {
        en: 'Cancel',
        zh: '取消'
    },
    confirm: {
        en: 'Confirm',
        zh: '确认'
    },
    ok: {
        en: 'OK',
        zh: '确定'
    },
    // Status message
    deploying: {
        en: 'Deploying workflow...',
        zh: '正在部署工作流...'
    },
    success: {
        en: 'Success',
        zh: '成功'
    },
    error: {
        en: 'Error',
        zh: '错误'
    },
    deploySuccess: {
        en: 'Workflow "{0}" deployed successfully!<br>Workflow ID: {1}<br>Version: {2}',
        zh: '工作流 "{0}" 部署成功！<br>工作流ID: {1}<br>版本: {2}'
    },
    updateSuccess: {
        en: 'Workflow "{0}" updated successfully!<br>Workflow ID: {1}<br>Version: {2}',
        zh: '工作流 "{0}" 更新成功！<br>工作流ID: {1}<br>版本: {2}'
    },
    deployFailed: {
        en: 'Failed to deploy workflow: {0}',
        zh: '部署工作流失败: {0}'
    },
    configEmpty: {
        en: 'API endpoint cannot be empty',
        zh: 'API 端点不能为空'
    }
};

function getText(key, ...args) {
    const lang = getUILanguage();
    let text = i18n[key][lang] || i18n[key]['en'] || key;
    
    // If there are parameters, format the replacement {0}, {1}, {2}...
    if (args && args.length > 0) {
        args.forEach((arg, index) => {
            text = text.replace(new RegExp('\\{' + index + '\\}', 'g'), arg);
        });
    }
    
    return text;
}

// Create deploy dialog
function createDeployDialog() {
    if (!deployDialog) {
        deployDialog = document.createElement('dialog');
        deployDialog.style.padding = '0';
        deployDialog.style.border = 'none';
        deployDialog.style.borderRadius = '12px';
        deployDialog.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.3)';
        
        const updateDialogContent = () => {
            deployDialog.innerHTML = `
                <div style="background:#1e1e1e; color:#fff; border-radius:12px; width:380px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:18px 24px; font-size:20px; font-weight:bold; border-bottom: 1px solid #333;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="background: #28a745; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                <i class="pi pi-upload" style="font-size: 16px;"></i>
                            </div>
                            ${getText('deployDialogTitle')}
                        </div>
                        <button id="deploy-dialog-close" style="background:transparent; border:none; color:#bbb; padding:0; cursor:pointer; font-size:24px;">×</button>
                    </div>
                    
                    <div style="padding:20px 24px 0;">
                        <div style="background: linear-gradient(45deg, #1a1a1a, #252525); border-radius: 8px; padding: 16px; margin-bottom: 20px; border: 1px solid #333;">
                            <p style="margin: 0 0 12px; font-size: 14px; color: #aaa; line-height: 1.4;">
                                ${getText('deployDescription')}
                            </p>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <i class="pi pi-info-circle" style="color: #4a9eff; font-size: 14px;"></i>
                                <span style="font-size: 13px; color: #4a9eff;">${getText('deployNodeInfo')}</span>
                            </div>
                        </div>
                        
                        <button id="deploy-dialog-deploy-btn" style="width:100%; background:#28a745; color:#fff; border:none; padding:14px; font-size:16px; border-radius:6px; display:flex; align-items:center; justify-content:center; gap:10px; margin-bottom:16px; transition: all 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.2); cursor: pointer; font-weight: 600;">
                            <i class="pi pi-cloud-upload" style="font-size: 18px;"></i> ${getText('deployButton')}
                        </button>
                        
                        <div style="display: flex; align-items: center; margin: 16px 0; color: #666;">
                            <div style="flex-grow: 1; height: 1px; background: #333;"></div>
                            <div style="margin: 0 10px; font-size: 13px;">${getText('configOptions')}</div>
                            <div style="flex-grow: 1; height: 1px; background: #333;"></div>
                        </div>
                        
                        <button id="deploy-dialog-config-btn" style="width:100%; background: linear-gradient(to bottom, #303030, #252525); color:#ddd; border:1px solid #444; padding:12px; font-size:15px; border-radius:6px; display:flex; align-items:center; justify-content:center; gap:8px; margin-bottom: 24px; transition: all 0.2s; cursor: pointer;">
                            <i class="pi pi-cog" style="font-size: 16px;"></i> ${getText('configApiButton')}
                        </button>
                    </div>
                    
                    <div style="background: #191919; padding: 16px 24px; border-top: 1px solid #333; border-radius: 0 0 12px 12px; font-size: 13px; color: #777; display: flex; align-items: center; justify-content: space-between;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div id="deploy-status-indicator" style="width: 8px; height: 8px; background: #28a745; border-radius: 50%;"></div>
                            <span id="deploy-status-text">${getText('statusReady')}</span>
                        </div>
                        <a href="https://github.com/ihmily/comfy-deploy-admin" target="_blank" style="color: #4a9eff; text-decoration: none; display: flex; align-items: center; gap: 5px;">
                            <i class="pi pi-github"></i>
                            ${getText('docs')}
                        </a>
                    </div>
                </div>
            `;
            
            deployDialog.querySelector('#deploy-dialog-close').onclick = () => deployDialog.close();
            deployDialog.querySelector('#deploy-dialog-deploy-btn').onclick = () => deployWorkflow();
            deployDialog.querySelector('#deploy-dialog-config-btn').onclick = () => openConfigDialog();
            
            const deployBtn = deployDialog.querySelector('#deploy-dialog-deploy-btn');
            deployBtn.addEventListener('mouseover', () => {
                deployBtn.style.background = '#2dbc4e';
                deployBtn.style.transform = 'translateY(-1px)';
            });
            deployBtn.addEventListener('mouseout', () => {
                deployBtn.style.background = '#28a745';
                deployBtn.style.transform = 'translateY(0)';
            });
            
            const configBtn = deployDialog.querySelector('#deploy-dialog-config-btn');
            configBtn.addEventListener('mouseover', () => {
                configBtn.style.background = '#353535';
            });
            configBtn.addEventListener('mouseout', () => {
                configBtn.style.background = 'linear-gradient(to bottom, #303030, #252525)';
            });
        };
        
        document.body.appendChild(deployDialog);
        
        // Initialize dialog content
        updateDialogContent();
        
        // Listen to language changes, update dialog content
        let lastLocale = app.ui.settings.getSettingValue('Comfy.Locale');
        setInterval(() => {
            try {
                const currentLocale = app.ui.settings.getSettingValue('Comfy.Locale');
                if (currentLocale !== lastLocale) {
                    lastLocale = currentLocale;
                    updateDialogContent();
                }
            } catch (e) {
                console.log('comfydeploy: Failed to get ComfyUI language settings, using default English', e);
            }
        }, 1000);
    }
    
    updateDeployStatus();
    
    return deployDialog;
}

function updateDeployStatus() {
    if (!deployDialog) return;
    
    const indicator = deployDialog.querySelector('#deploy-status-indicator');
    const statusText = deployDialog.querySelector('#deploy-status-text');
    
    if (!deployConfig.endpoint || !deployConfig.apiKey) {
        indicator.style.background = '#ff9800'; // Yellow warning
        statusText.textContent = getText('configRequired');
        return;
    }
    
    // Test connection
    fetch(deployConfig.endpoint + '/workflows/status', { 
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${deployConfig.apiKey}`
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data && data.status === 'ok') {
            indicator.style.background = '#28a745'; // Green success
            statusText.textContent = getText('statusConnected');
        } else {
            indicator.style.background = '#ff4d4d'; // Red error
            statusText.textContent = getText('statusFailed');
        }
    })
    .catch(error => {
        indicator.style.background = '#ff4d4d'; // Red error
        statusText.textContent = getText('statusFailed');
    });
}

// Open deploy dialog
function openDeployDialog() {
    const dialog = createDeployDialog();
    dialog.showModal();
}

function openConfigDialog() {
    let dialog = document.getElementById('comfy-api-deploy-config-dialog');
    if (!dialog) {
        dialog = document.createElement('dialog');
        dialog.id = 'comfy-api-deploy-config-dialog';
        dialog.style.padding = '0';
        dialog.style.border = 'none';
        dialog.style.borderRadius = '12px';
        dialog.style.boxShadow = 'none';
        dialog.innerHTML = `
            <div style="background:#1e1e1e; color:#fff; border-radius:12px; width:400px;">
                <div style="display:flex; justify-content:space-between; align-items:center; padding:16px 24px; font-size:18px; font-weight:bold;">
                    ${getText('configTitle')}
                    <button id="comfy-api-deploy-config-close-x" style="background:transparent; border:none; color:#bbb; padding:0; cursor:pointer; font-size:24px;">×</button>
                </div>
                <div style="padding:0 24px 16px;">
                    <label style="display:block; margin-bottom:12px;">
                        ${getText('endpointLabel')}
                        <input type="text" id="comfy-api-deploy-config-endpoint" placeholder="${getText('endpointPlaceholder')}" style="width:100%; padding:8px; margin-top:4px; border-radius:4px; border:1px solid #444; background:#2b2c2e; color:#fff;"/>
                    </label>
                    <label style="display:block; margin-bottom:12px;">
                        ${getText('apiKeyLabel')}
                        <input type="text" id="comfy-api-deploy-config-api-key" placeholder="${getText('apiKeyPlaceholder')}" style="width:100%; padding:8px; margin-top:4px; border-radius:4px; border:1px solid #444; background:#2b2c2e; color:#fff;"/>
                    </label>
                </div>
                <div style="display:flex; justify-content:flex-end; gap:8px; padding:12px 24px; border-top:1px solid #333;">
                    <button id="comfy-api-deploy-config-close" style="background:transparent; border:none; color:#bbb; padding:8px 16px; cursor:pointer;">${getText('cancel')}</button>
                    <button id="comfy-api-deploy-config-save" style="background:#28a745; border:none; color:#fff; padding:8px 16px; cursor:pointer; border-radius:4px;">${getText('save')}</button>
                </div>
            </div>
        `;
        document.body.appendChild(dialog);
        dialog.querySelector('#comfy-api-deploy-config-close-x').onclick = () => dialog.close();
        dialog.querySelector('#comfy-api-deploy-config-close').onclick = () => dialog.close();
        dialog.querySelector('#comfy-api-deploy-config-save').onclick = () => {
            const endpoint = document.getElementById('comfy-api-deploy-config-endpoint').value.trim();
            const apiKey = document.getElementById('comfy-api-deploy-config-api-key').value.trim();
            
            if (!endpoint) {
                showMessage(getText('error'), getText('configEmpty'), true);
                return;
            }
            
            // Save config
            const success = saveConfig({ endpoint, apiKey });
            
            if (success) {
                dialog.close();
                updateDeployStatus();
            }
        };
    }
    
    // Fill current config
    dialog.querySelector('#comfy-api-deploy-config-endpoint').value = deployConfig.endpoint || '';
    dialog.querySelector('#comfy-api-deploy-config-api-key').value = deployConfig.apiKey || '';
    
    dialog.showModal();
}

function showMessage(title, message, isError = false) {
    let dialog = document.createElement('dialog');
    dialog.style.padding = '0';
    dialog.style.border = 'none';
    dialog.style.borderRadius = '12px';
    dialog.style.boxShadow = 'none';
        dialog.innerHTML = `
            <div style="background:#1e1e1e; color:#fff; border-radius:12px; width:400px;">
                <div style="display:flex; justify-content:space-between; align-items:center; padding:16px 20px; font-size:18px; font-weight:bold; color:${isError ? '#ff4d4d' : '#fff'}">
                    ${title}
                    <button class="dialog-close-x" style="background:transparent; border:none; color:#bbb; padding:0; cursor:pointer; font-size:24px;">×</button>
                </div>
                <div style="padding:5px 20px 16px;">
                    <p style="line-height:1.5; font-size:14px; margin:8px 0;">${message}</p>
                </div>
                <div style="display:flex; justify-content:flex-end; gap:8px; padding:12px 20px; border-top:1px solid #333;">
                    <button class="dialog-close" style="background:#28a745; border:none; color:#fff; padding:8px 20px; cursor:pointer; border-radius:4px; font-size:14px;">${getText('ok')}</button>
                </div>
            </div>
        `;
    document.body.appendChild(dialog);
    dialog.querySelector('.dialog-close-x').onclick = () => {
        dialog.close();
        dialog.remove();
    };
    dialog.querySelector('.dialog-close').onclick = () => {
        dialog.close();
        dialog.remove();
    };
    dialog.showModal();
}

function showLoading(message) {
    let dialog = document.createElement('dialog');
    dialog.id = 'comfy-api-deploy-loading';
    dialog.style.padding = '0';
    dialog.style.border = 'none';
    dialog.style.borderRadius = '12px';
    dialog.style.boxShadow = 'none';
    dialog.innerHTML = `
        <div style="background:#1e1e1e; color:#fff; border-radius:12px; width:400px; padding:24px; text-align:center;">
            <div style="margin-bottom:16px;">
                <i class="pi pi-spinner pi-spin" style="font-size:32px;"></i>
            </div>
            <p>${message}</p>
        </div>
    `;
    document.body.appendChild(dialog);
    dialog.showModal();
    return dialog;
}

function showConfirmDialog(title, message) {
    return new Promise((resolve) => {
        let dialog = document.createElement('dialog');
        dialog.style.padding = '0';
        dialog.style.border = 'none';
        dialog.style.borderRadius = '12px';
        dialog.style.boxShadow = 'none';
        dialog.innerHTML = `
            <div style="background:#1e1e1e; color:#fff; border-radius:12px; width:400px;">
                <div style="display:flex; justify-content:space-between; align-items:center; padding:16px 20px; font-size:18px; font-weight:bold;">
                    ${title}
                    <button class="dialog-close-x" style="background:transparent; border:none; color:#bbb; padding:0; cursor:pointer; font-size:24px;">×</button>
                </div>
                <div style="padding:5px 20px 16px;">
                    <div style="line-height:1.5; font-size:14px; margin:8px 0;">${message}</div>
                </div>
                <div style="display:flex; justify-content:flex-end; gap:10px; padding:12px 20px; border-top:1px solid #333;">
                    <button class="dialog-cancel" style="background:#333; border:1px solid #555; color:#eee; padding:8px 16px; cursor:pointer; border-radius:4px; font-size:14px; transition:all 0.2s;">${getText('cancel')}</button>
                    <button class="dialog-confirm" style="background:#28a745; border:none; color:#fff; padding:8px 20px; cursor:pointer; border-radius:4px; font-size:14px; transition:all 0.2s;">${getText('confirm')}</button>
                </div>
            </div>
        `;
        document.body.appendChild(dialog);
        
        const cancelBtn = dialog.querySelector('.dialog-cancel');
        cancelBtn.addEventListener('mouseover', () => {
            cancelBtn.style.background = '#444';
        });
        cancelBtn.addEventListener('mouseout', () => {
            cancelBtn.style.background = '#333';
        });
        
        const confirmBtn = dialog.querySelector('.dialog-confirm');
        confirmBtn.addEventListener('mouseover', () => {
            confirmBtn.style.background = '#2dbc4e';
            confirmBtn.style.transform = 'translateY(-1px)';
        });
        confirmBtn.addEventListener('mouseout', () => {
            confirmBtn.style.background = '#28a745';
            confirmBtn.style.transform = 'translateY(0)';
        });
        
        dialog.querySelector('.dialog-close-x').onclick = () => {
            dialog.close();
            dialog.remove();
            resolve(false);
        };
        
        dialog.querySelector('.dialog-cancel').onclick = () => {
            dialog.close();
            dialog.remove();
            resolve(false);
        };
        
        dialog.querySelector('.dialog-confirm').onclick = () => {
            dialog.close();
            dialog.remove();
            resolve(true);
        };
        
        dialog.showModal();
    });
}

function showInputDialog(title, placeholder = '') {
    return new Promise((resolve) => {
        let dialog = document.createElement('dialog');
        dialog.style.padding = '0';
        dialog.style.border = 'none';
        dialog.style.borderRadius = '12px';
        dialog.style.boxShadow = 'none';
        dialog.innerHTML = `
            <div style="background:#1e1e1e; color:#fff; border-radius:12px; width:400px;">
                <div style="display:flex; justify-content:space-between; align-items:center; padding:16px 20px; font-size:18px; font-weight:bold;">
                    ${title}
                    <button class="dialog-close-x" style="background:transparent; border:none; color:#bbb; padding:0; cursor:pointer; font-size:24px;">×</button>
                </div>
                <div style="padding:5px 20px 16px;">
                    <input type="text" id="input-dialog-text" placeholder="${placeholder}" 
                           style="width:100%; padding:10px; background:#2b2c2e; color:#fff; border:1px solid #444; 
                                  border-radius:4px; font-size:14px; margin-top:8px; box-sizing:border-box; box-shadow:0 2px 5px rgba(0,0,0,0.1) inset;">
                </div>
                <div style="display:flex; justify-content:flex-end; gap:10px; padding:12px 20px; border-top:1px solid #333;">
                    <button class="dialog-cancel" style="background:#333; border:1px solid #555; color:#eee; padding:8px 16px; cursor:pointer; border-radius:4px; font-size:14px; transition:all 0.2s;">${getText('cancel')}</button>
                    <button class="dialog-confirm" style="background:#28a745; border:none; color:#fff; padding:8px 20px; cursor:pointer; border-radius:4px; font-size:14px; transition:all 0.2s;">${getText('ok')}</button>
                </div>
            </div>
        `;
        document.body.appendChild(dialog);
        
        const inputElement = dialog.querySelector('#input-dialog-text');
        
        dialog.addEventListener('click', () => {
            inputElement.focus();
        });
        
        setTimeout(() => {
            inputElement.focus();
        }, 100);
        
        inputElement.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const inputValue = inputElement.value.trim();
                if (inputValue) {
                    dialog.close();
                    dialog.remove();
                    resolve(inputValue);
                }
            }
        });
        
        const cancelBtn = dialog.querySelector('.dialog-cancel');
        cancelBtn.addEventListener('mouseover', () => {
            cancelBtn.style.background = '#444';
        });
        cancelBtn.addEventListener('mouseout', () => {
            cancelBtn.style.background = '#333';
        });
        
        const confirmBtn = dialog.querySelector('.dialog-confirm');
        confirmBtn.addEventListener('mouseover', () => {
            confirmBtn.style.background = '#2dbc4e';
            confirmBtn.style.transform = 'translateY(-1px)';
        });
        confirmBtn.addEventListener('mouseout', () => {
            confirmBtn.style.background = '#28a745';
            confirmBtn.style.transform = 'translateY(0)';
        });
        
        dialog.querySelector('.dialog-close-x').onclick = () => {
            dialog.close();
            dialog.remove();
            resolve(null);
        };
        
        dialog.querySelector('.dialog-cancel').onclick = () => {
            dialog.close();
            dialog.remove();
            resolve(null);
        };
        
        dialog.querySelector('.dialog-confirm').onclick = () => {
            const inputValue = inputElement.value.trim();
            dialog.close();
            dialog.remove();
            resolve(inputValue);
        };
        
        dialog.showModal();
    });
}

async function deployWorkflow() {
    if (!deployConfig.endpoint || !deployConfig.apiKey) {
        showMessage(getText('error'), getText('configRequired'), true);
        openConfigDialog();
        return;
    }
    
    // Find ComfyDeploy node in the workflow
    let deployNodes = app.graph.findNodesByType("comfy-deploy/comfy-deploy");
    
    let workflowName = "";
    let workflowId = "";
    let version = "";
    
    // If node is found, use the values from the node
    if (deployNodes.length > 0) {
        const deployNode = deployNodes[0];
        workflowName = deployNode.widgets[0].value || "";
        workflowId = deployNode.widgets[1].value || "";
        version = deployNode.widgets[2].value || "";
    }
    
    // If no workflow name is found, use custom dialog to prompt user to input
    if (!workflowName) {
        workflowName = await showInputDialog(getText('enterWorkflowName'), getText('inputWorkflowName'));
        if (!workflowName) {
            return;
        }
    }
    
    let confirmMessage;
    if (workflowId) {
        confirmMessage = `
            <div style="margin-bottom:12px">${getText('createNewVersion')} <span style="font-weight:bold;">${workflowName}</span>.</div>
            <div style="margin-top:16px; margin-bottom:6px"><b>${getText('workflowId')}:</b> <span style="font-family:monospace; background:#252525; padding:2px 6px; border-radius:3px;">${workflowId}</span></div>
            <div><b>${getText('currentVersion')}:</b> <span style="font-family:monospace; background:#252525; padding:2px 6px; border-radius:3px;">${version}</span></div>
        `;
    } else {
        confirmMessage = `<div>${getText('createNewWorkflow')} <span style="font-weight:bold;">${workflowName}</span>.</div>`;
    }
    
    const confirmed = await showConfirmDialog(getText('confirmDeploy'), confirmMessage);
    if (!confirmed) return;
    
    if (deployDialog && deployDialog.open) {
        deployDialog.close();
    }
    
    const loadingDialog = showLoading(getText('deploying'));
    
    try {
        const prompt = await app.graphToPrompt();
        
        const requestData = {
            // workflow: prompt.workflow, // Workflow graph data
            prompt_template: JSON.stringify(prompt.output),
            workflow_graph: JSON.stringify(prompt.workflow),
        };
        
        let url, method;
        if (workflowId) {
            // update workflow
            url = `${deployConfig.endpoint}/workflows/${workflowId}`;
            method = 'PUT';
        } else {
            // new workflow
            url = `${deployConfig.endpoint}/workflows`;
            method = 'POST';
            requestData.workflow_name = workflowName;
        }
        
        // Create timeout controller (10 seconds)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        let response;
        try {
            response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${deployConfig.apiKey}`
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error(getText('deployFailed', 'Request timed out (10 seconds)'));
            }
            throw error;
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || getText('deployFailed', ''));
        }
        
        const data = await response.json();
        
        const responseWorkflowName = data.workflow_name || workflowName;
        
        updateOrCreateDeployNode(responseWorkflowName, data.id, data.latest_version || "v1");
        
        loadingDialog.close();
        loadingDialog.remove();
        
        const messageKey = workflowId ? 'updateSuccess' : 'deploySuccess';
        const formattedMessage = getText(messageKey, responseWorkflowName, data.id, data.latest_version || "v1")
            .replace('<br>', '<br><br>')
            .replace('Workflow ID:', '<b>Workflow ID:</b>')
            .replace('工作流ID:', '<b>工作流ID:</b>')
            .replace('Version:', '<b>Version:</b>')
            .replace('版本:', '<b>版本:</b>');
        showMessage(getText('success'), formattedMessage);
    } catch (error) {
        loadingDialog.close();
        loadingDialog.remove();
        showMessage(getText('error'), getText('deployFailed', error.message), true);
    }
}

function updateOrCreateDeployNode(workflowName, workflowId, version) {
    let deployNodes = app.graph.findNodesByType("comfy-deploy/comfy-deploy");
    
    if (deployNodes.length === 0) {
        // If node does not exist, create a new node
        app.graph.beforeChange();
        const node = LiteGraph.createNode("comfy-deploy/comfy-deploy");
        
        node.properties = {
            workflow_name: workflowName,
            workflow_id: workflowId,
            version: version
        };
        
        node.widgets[0].value = workflowName;
        node.widgets[1].value = workflowId;
        node.widgets[2].value = version;
        
        // Place node in the appropriate position in the canvas visible area
        const canvasCenter = [
            app.canvas.canvas.width / (2 * app.canvas.ds.scale) - app.canvas.ds.offset[0] / app.canvas.ds.scale,
            app.canvas.canvas.height / (2 * app.canvas.ds.scale) - app.canvas.ds.offset[1] / app.canvas.ds.scale
        ];
        node.pos = [canvasCenter[0] - 100, canvasCenter[1] - 50];
        
        app.graph.add(node);
        app.graph.afterChange();
        
        app.graph.config_id = "last_saved_config_" + Date.now();
        localStorage.setItem("litegraphDiagram", JSON.stringify(app.graph.serialize()));
    } else {
        const deployNode = deployNodes[0];
        
        deployNode.properties.workflow_name = workflowName;
        deployNode.properties.workflow_id = workflowId;
        deployNode.properties.version = version;
        
        deployNode.widgets[0].value = workflowName;
        deployNode.widgets[1].value = workflowId;
        deployNode.widgets[2].value = version;
        
        app.graph.setDirtyCanvas(true, true);
        app.graph.change();
        
        app.graph.config_id = "last_saved_config_" + Date.now();
        localStorage.setItem("litegraphDiagram", JSON.stringify(app.graph.serialize()));
    }
}

app.registerExtension({
    name: 'Comfy Deploy Panel:SidebarTab',
    async setup() {
        loadConfig();
        
        // Compatible with old UI: insert into main menu (left side)
        const interval = setInterval(() => {
            const menu = document.querySelector('.comfy-menu');
            if (!menu) return;
            clearInterval(interval);
            if (menu.querySelector('#comfy-api-deploy-menu-btn')) return;
            const btn = document.createElement('button');
            btn.id = 'comfy-api-deploy-menu-btn';
            btn.className = 'comfy-menu-button';
            btn.title = 'Comfy Deploy';
            btn.innerText = 'ComfyDeploy';
            btn.onclick = () => {
                openDeployDialog();
            };
            menu.appendChild(btn);
        }, 100);
        
        const updateButtonText = (btn) => {
            if (!btn) return;
            
            const label = btn.querySelector('.side-bar-button-label');
            if (!label) return;
            
            // Use ComfyUI's settings API to get interface language
            let buttonText = 'Deploy';
            try {
                const locale = app.ui.settings.getSettingValue('Comfy.Locale');
                if (locale && locale.toLowerCase().startsWith('zh')) {
                    buttonText = '部署';
                }
            } catch (e) {
                console.log('comfydeploy: Failed to get ComfyUI language settings, using default English', e);
            }
            
            label.textContent = buttonText;
        };
        
        // Compatible with new UI: insert into sidebar (right side)
        const newUIInterval = setInterval(() => {
            const sideToolBar = document.querySelector('.side-tool-bar-container');
            if (!sideToolBar) return;
            clearInterval(newUIInterval);
            if (sideToolBar.querySelector('#comfy-deploy-sidebar-btn')) return;
            
            const btn = document.createElement('button');
            btn.id = 'comfy-deploy-sidebar-btn';
            btn.className = 'p-button p-component p-button-icon-only p-button-text side-bar-button p-button-secondary';
            btn.type = 'button';
            btn.setAttribute('aria-label', 'ComfyDeploy');
            btn.setAttribute('data-pc-name', 'button');
            btn.setAttribute('data-p-disabled', 'false');
            btn.setAttribute('data-pc-section', 'root');
            btn.setAttribute('data-pd-tooltip', 'true');
            btn.style.width = '64px';
            btn.style.height = '72px';
            btn.style.padding = '8px 0px';
            btn.style.boxSizing = 'border-box';
            
            const btnContent = document.createElement('div');
            btnContent.className = 'side-bar-button-content';
            btnContent.style.display = 'flex';
            btnContent.style.flexDirection = 'column';
            btnContent.style.alignItems = 'center';
            btnContent.style.justifyContent = 'center';
            btnContent.style.height = '100%';
            
            // Create icon
            const icon = document.createElement('i');
            icon.className = 'pi pi-cloud-upload side-bar-button-icon';
            icon.style.fontSize = '16px';
            icon.style.marginBottom = '4px';
            
            // Create label
            const label = document.createElement('span');
            label.className = 'side-bar-button-label';
            label.style.fontSize = '10px';
            
            btnContent.appendChild(icon);
            btnContent.appendChild(label);
            btn.appendChild(btnContent);
            
            const buttonLabel = document.createElement('span');
            buttonLabel.className = 'p-button-label';
            buttonLabel.innerHTML = '&nbsp;';
            buttonLabel.setAttribute('data-pc-section', 'label');
            btn.appendChild(buttonLabel);
            
            // Add click event
            btn.onclick = () => {
                openDeployDialog();
            };
            
            const templateButton = sideToolBar.querySelector('.templates-tab-button');
            
            if (templateButton) {
                templateButton.after(btn);
            } else {
                const firstButton = sideToolBar.querySelector('button');
                if (firstButton) {
                    firstButton.after(btn);
                } else {
                    sideToolBar.appendChild(btn);
                }
            }
            
            updateButtonText(btn);
            
            // Use timer to check if language settings change
            let lastLocale = app.ui.settings.getSettingValue('Comfy.Locale');
            setInterval(() => {
                try {
                    const currentLocale = app.ui.settings.getSettingValue('Comfy.Locale');
                    if (currentLocale !== lastLocale) {
                        lastLocale = currentLocale;
                        updateButtonText(btn);
                    }
                } catch (e) {
                    console.log('comfydeploy: Failed to get ComfyUI language settings, using default English', e);
                }
            }, 1000);
        }, 100);
    }
});
