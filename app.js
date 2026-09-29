document.addEventListener('DOMContentLoaded', () => {
    let isCopying = false;
    window.addEventListener('pywebviewready', () => {
        initFileBrowser();
        setInterval(async () => {
            if (!isCopying) {
                const browser = document.getElementById('source-browser');
                await loadDirectory('ROOT', browser, 0, true);
                
                const openUls = document.querySelectorAll('ul.file-list:not(.hidden)');
                for (let ul of openUls) {
                    let path = ul.dataset.path;
                    let level = parseInt(ul.dataset.level || "0");
                    if (path) {
                        await loadDirectory(path, ul, level, false);
                    }
                }
            }
        }, 3000);
    });
    
    // Hamburger Menu Logic
    const settingsToggle = document.getElementById('settings-toggle');
    const settingsPanel = document.getElementById('settings-panel');
    const closeSettings = document.getElementById('close-settings');

    settingsToggle.addEventListener('click', () => {
        settingsPanel.classList.add('open');
    });
    closeSettings.addEventListener('click', () => {
        settingsPanel.classList.remove('open');
    });

    const sourceDropZone = document.getElementById('source-list');
    const destDropZone = document.getElementById('dest-list');
    let draggedItemData = null;

    const directoryCache = new Map();
    const expandedPaths = new Set();

    async function loadDirectory(path, container, level, isRoot = false) {
        try {
            let items;
            if (isRoot) {
                items = await pywebview.api.get_root_directories();
            } else {
                items = await pywebview.api.list_directory(path);
            }
            const itemsStr = JSON.stringify(items);
            const cacheKey = isRoot ? 'ROOT' : path;
            
            if (directoryCache.get(cacheKey) !== itemsStr) {
                directoryCache.set(cacheKey, itemsStr);
                container.innerHTML = '';
                renderFileList(items, container, level);
            }
        } catch (error) {
            console.error("Error loading directory", error);
        }
    }

    async function initFileBrowser() {
        const browser = document.getElementById('source-browser');
        await loadDirectory('ROOT', browser, 0, true);
    }

    function getIconForKind(kind, type) {
        if (type === 'drive') return '💽';
        if (type === 'home' || type === 'user') return '🏠';
        if (type === 'folder') return '📁';
        if (kind.includes('PDF')) return '📄';
        if (kind.includes('影像')) return '🖼️';
        if (kind.includes('影片')) return '🎬';
        if (kind.includes('HTML') || kind.includes('Javascript') || kind.includes('CSS') || kind.includes('Markdown')) return '📝';
        return '📄';
    }

    function renderFileList(items, containerElement, level) {
        items.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = `finder-row ${item.type}`;
            // Base padding + indentation
            const paddingLeft = level * 16 + 8;
            
            li.draggable = true;
            li.dataset.type = item.type;
            li.dataset.path = item.path;
            
            // Layout: [Arrow] [Icon] [Name]        [Date]     [Size]   [Kind]
            // We use CSS Grid for this.
            
            let arrowHtml = `<span class="finder-arrow" style="margin-left: ${paddingLeft}px; visibility: ${item.is_dir ? 'visible' : 'hidden'}">›</span>`;
            let iconHtml = `<span class="finder-icon">${getIconForKind(item.kind, item.type)}</span>`;
            
            li.innerHTML = `
                <div class="finder-col-name">
                    ${arrowHtml}
                    ${iconHtml}
                    <span class="finder-name-text">${item.name}</span>
                </div>
                <div class="finder-col-date">${item.date}</div>
                <div class="finder-col-size">${item.size}</div>
                <div class="finder-col-kind">${item.kind}</div>
            `;

            // Container for children
            const childrenContainer = document.createElement('ul');
            childrenContainer.className = 'file-list hidden';
            childrenContainer.dataset.path = item.path;
            childrenContainer.dataset.level = level + 1;
            
            let isLoaded = false;
            let isOpen = false;

            if (item.is_dir) {
                li.style.cursor = 'pointer';
                
                const toggleFolder = async () => {
                    const arrow = li.querySelector('.finder-arrow');
                    if (!isOpen) {
                        isOpen = true;
                        expandedPaths.add(item.path);
                        childrenContainer.classList.remove('hidden');
                        arrow.classList.add('open');
                        
                        if (!isLoaded) {
                            await loadDirectory(item.path, childrenContainer, level + 1, false);
                            isLoaded = true;
                        }
                    } else {
                        isOpen = false;
                        expandedPaths.delete(item.path);
                        childrenContainer.classList.add('hidden');
                        arrow.classList.remove('open');
                    }
                };

                li.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    await toggleFolder();
                });

                if (expandedPaths.has(item.path)) {
                    isOpen = true;
                    childrenContainer.classList.remove('hidden');
                    li.querySelector('.finder-arrow').classList.add('open');
                    isLoaded = true;
                    loadDirectory(item.path, childrenContainer, level + 1, false);
                }
            }

            li.addEventListener('dragstart', (e) => {
                e.stopPropagation(); 
                draggedItemData = {
                    name: item.name,
                    path: item.path,
                    type: item.type,
                    icon: getIconForKind(item.kind, item.type)
                };
                e.dataTransfer.setData('text/plain', item.name);
                e.dataTransfer.effectAllowed = 'copy';
            });

            containerElement.appendChild(li);
            if (item.is_dir) {
                containerElement.appendChild(childrenContainer);
            }
        });
    }

    const setupDropZone = (zone) => {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });
        zone.addEventListener('click', async (e) => {
            // Prevent triggering if clicking on an already dropped item's remove button
            if (e.target.closest('.dropped-item')) return;
            
            let result;
            if (zone === sourceDropZone) {
                let wantFolder = confirm("要選擇整個「資料夾」嗎？\n(按「確定」選擇資料夾，按「取消」選擇檔案)");
                if (wantFolder) {
                    result = await pywebview.api.select_folder();
                } else {
                    result = await pywebview.api.select_files();
                }
            } else {
                result = await pywebview.api.select_folder();
            }
            
            if (result && result.length > 0) {
                let itemsToProcess = [];
                for (let absolutePath of result) {
                    let itemInfo = await pywebview.api.get_file_info_from_path(absolutePath);
                    if (itemInfo) {
                        itemInfo.icon = getIconForKind(itemInfo.kind, itemInfo.type);
                        itemsToProcess.push(itemInfo);
                    }
                }
                processDroppedItems(zone, itemsToProcess);
            }
        });

        zone.addEventListener('drop', async (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            
            let itemsToProcess = [];
            
            if (draggedItemData) {
                itemsToProcess.push(draggedItemData);
            } else if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                for (let i = 0; i < e.dataTransfer.files.length; i++) {
                    let file = e.dataTransfer.files[i];
                    // Chromium / Some WebKit wrappers expose .path
                    let absolutePath = file.path || (file.webkitRelativePath ? file.webkitRelativePath : null) || (file.name.includes('/') ? file.name : null);
                    if (absolutePath) {
                        let itemInfo = await pywebview.api.get_file_info_from_path(absolutePath);
                        if (itemInfo) {
                            itemInfo.icon = getIconForKind(itemInfo.kind, itemInfo.type);
                            itemsToProcess.push(itemInfo);
                        }
                    } else {
                        alert(`抱歉，目前的權限無法直接從 Finder 拖曳 (${file.name} 缺少絕對路徑)。請從左側的「檔案瀏覽器」拖曳。`);
                        return;
                    }
                }
            }

            if (itemsToProcess.length > 0) {
                processDroppedItems(zone, itemsToProcess);
            }
        });
        
        async function processDroppedItems(zone, itemsToProcess) {
            for (let data of itemsToProcess) {
                const placeholder = zone.querySelector('.drop-placeholder');
                if (placeholder) placeholder.style.display = 'none';

                let formatBadge = "";
                if (zone === sourceDropZone && (data.type === 'folder' || data.type === 'drive' || data.type === 'home')) {
                    try {
                        const cardFormat = await pywebview.api.detect_card_format(data.path);
                        if (cardFormat) {
                            formatBadge = `<span class="format-badge" style="background:var(--bg-success); color:white; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 8px; font-weight: bold; box-shadow: var(--glass-shadow);">${cardFormat}</span>`;
                        }
                    } catch(err) {
                        console.error("Format detect error", err);
                    }
                }

                const el = document.createElement('div');
                el.className = 'dropped-item';
                el.dataset.path = data.path; 
                el.innerHTML = `
                    <div class="dropped-info">
                        <span class="dropped-name">${data.icon} ${data.name} ${formatBadge}</span>
                        <span class="dropped-path">${data.path}</span>
                    </div>
                    <span class="remove-item">×</span>
                `;
                
                el.querySelector('.remove-item').addEventListener('click', () => {
                    el.remove();
                    if (zone.querySelectorAll('.dropped-item').length === 0) {
                        if(placeholder) placeholder.style.display = 'flex';
                    }
                    if (sourceDropZone.querySelectorAll('.dropped-item').length === 0 && destDropZone.querySelectorAll('.dropped-item').length === 0) {
                        resetUI();
                    }
                });

                zone.appendChild(el);
            }
        }
    };

    setupDropZone(sourceDropZone);
    setupDropZone(destDropZone);

    const startBtn = document.getElementById('start-copy-btn');
    const openFolderBtn = document.getElementById('open-folder-btn');
    const speedText = document.getElementById('speed-text');
    const filesText = document.getElementById('files-text');

    startBtn.addEventListener('click', async () => {
        if (startBtn.textContent === '完成') {
            resetUI();
            return;
        }
        if (isCopying) return;
        
        const sourceItems = Array.from(sourceDropZone.querySelectorAll('.dropped-item')).map(el => el.dataset.path);
        const destItems = Array.from(destDropZone.querySelectorAll('.dropped-item')).map(el => el.dataset.path);

        if (sourceItems.length === 0 || destItems.length === 0) {
            alert('請先拖曳來源檔案與目的資料夾');
            return;
        }

        isCopying = true;
        startBtn.disabled = true;
        startBtn.textContent = '掃描中...';
        document.body.className = 'status-copying';
        
        // Scan files
        let scanResult;
        try {
            scanResult = await pywebview.api.scan_files(sourceItems);
            filesText.textContent = `0 / ${scanResult.total_files} 檔案`;
        } catch(e) {
            console.error("Scan error", e);
            alert("掃描失敗");
            resetUI();
            return;
        }

        // Gather settings safely
        const collisionModeEl = document.getElementById('collision-mode');
        const settings = {
            use_xxhash: document.getElementById('use-xxhash')?.checked || false,
            use_md5: document.getElementById('use-md5')?.checked || false,
            export_pdf: document.getElementById('export-pdf')?.checked || false,
            export_csv: document.getElementById('export-csv')?.checked || false,
            collision_mode: collisionModeEl ? collisionModeEl.value : '自動更名加序號'
        };

        // Start copy
        startBtn.textContent = '拷貝中...';
        await pywebview.api.start_copy(sourceItems, destItems, settings);
        
        // Poll progress
        const interval = setInterval(async () => {
            const status = await pywebview.api.get_copy_progress();
            
            document.getElementById('p1-bar').style.width = `${status.p1}%`;
            document.getElementById('p2-bar').style.width = `${status.p2}%`;
            document.getElementById('p3-bar').style.width = `${status.p3}%`;
            
            document.getElementById('p1-text').textContent = `${status.p1.toFixed(1)}%`;
            document.getElementById('p2-text').textContent = `${status.p2.toFixed(1)}%`;
            document.getElementById('p3-text').textContent = `${status.p3.toFixed(1)}%`;
            speedText.textContent = `${status.speed.toFixed(1)} MB/s`;
            filesText.textContent = `${status.copied_files} / ${status.total_files} 檔案`;

            let etaStr = "--:--";
            if (status.eta > 0) {
                let totalSecs = Math.floor(status.eta);
                let m = Math.floor(totalSecs / 60);
                let s = totalSecs % 60;
                let h = Math.floor(m / 60);
                m = m % 60;
                if (h > 0) {
                    etaStr = `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
                } else {
                    etaStr = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
                }
            } else if (status.speed > 0 && status.p3 === 100) {
                etaStr = "00:00";
            }
            document.getElementById('eta-text').textContent = `預計剩餘時間: ${etaStr}`;

            if (status.status === 'done') {
                clearInterval(interval);
                finishCopy();
            } else if (status.status === 'error') {
                clearInterval(interval);
                document.body.className = 'status-error';
                const soundAlert = document.getElementById('sound-alert');
                if (soundAlert && soundAlert.checked) {
                    pywebview.api.play_error_sound();
                }
                setTimeout(() => {
                    alert("拷貝過程發生錯誤或已被中止（例如：發現同名檔案）。請查看報告或日誌。");
                    resetUI(true);
                }, 100);
            }
        }, 300);
    });

    function finishCopy() {
        document.body.className = 'status-success';
        startBtn.textContent = '完成';
        startBtn.style.background = 'var(--bg-success)';
        startBtn.disabled = false;
        
        const soundAlert = document.getElementById('sound-alert');
        if (soundAlert && soundAlert.checked) {
            pywebview.api.play_completion_sound();
        }
        
        document.getElementById('p1-bar').style.width = `100%`;
        document.getElementById('p2-bar').style.width = `100%`;
        document.getElementById('p3-bar').style.width = `100%`;
        document.getElementById('p1-text').textContent = `100.0%`;
        document.getElementById('p2-text').textContent = `100.0%`;
        document.getElementById('p3-text').textContent = `100.0%`;
        speedText.textContent = '-- MB/s';
        document.getElementById('eta-text').textContent = '預計剩餘時間: 00:00';
        openFolderBtn.classList.remove('hidden');
    }

    openFolderBtn.addEventListener('click', () => {
        const destItems = Array.from(destDropZone.querySelectorAll('.dropped-item')).map(el => el.dataset.path);
        if (destItems.length > 0) {
            pywebview.api.open_folder(destItems[0]);
        }
    });

    function resetUI(isError = false) {
        isCopying = false;
        startBtn.disabled = false;
        startBtn.textContent = '開始安全拷貝';
        startBtn.style.background = '';
        openFolderBtn.classList.add('hidden');
        document.body.className = isError ? 'status-error' : 'status-idle';
        document.getElementById('p1-bar').style.width = `0%`;
        document.getElementById('p2-bar').style.width = `0%`;
        document.getElementById('p3-bar').style.width = `0%`;
        document.getElementById('p1-text').textContent = `等待開始...`;
        document.getElementById('p2-text').textContent = `等待開始...`;
        document.getElementById('p3-text').textContent = `等待開始...`;
        filesText.textContent = '0 / 0 檔案';
        document.getElementById('eta-text').textContent = '預計剩餘時間: --:--';
    }
});
