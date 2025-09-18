/**
 * History Viewer - Reconstruct historical versions of pages using RSS feed diffs
 */
(function() {
    'use strict';

    class HistoryViewer {
        constructor() {
            this.currentContent = null;
            this.rssEntries = [];
            this.feedUrl = null;
            this.initialized = false;
        }

        async init() {
            // Get RSS feed URL from meta tag
            const feedMeta = document.querySelector('meta[name="rss-feed-url"]');
            if (!feedMeta) {
                console.error('No RSS feed URL found in meta tags');
                return;
            }

            this.feedUrl = feedMeta.content;
            this.currentContent = document.body.innerHTML;

            // Check for date parameter in URL
            const urlParams = new URLSearchParams(window.location.search);
            const targetDate = urlParams.get('date');

            // Load RSS feed
            await this.loadRSSFeed();

            // Create UI
            this.createUI();

            // If date parameter exists, reconstruct that version
            if (targetDate) {
                await this.reconstructVersion(targetDate);
            }

            this.initialized = true;
        }

        async loadRSSFeed() {
            try {
                const response = await fetch(this.feedUrl);
                const text = await response.text();
                const parser = new DOMParser();
                const xml = parser.parseFromString(text, 'text/xml');

                // Parse RSS items
                const items = xml.querySelectorAll('item');
                this.rssEntries = Array.from(items).map(item => {
                    const description = item.querySelector('description')?.textContent || '';
                    const pubDate = item.querySelector('pubDate')?.textContent || '';
                    const link = item.querySelector('link')?.textContent || '';
                    const guid = item.querySelector('guid')?.textContent || '';

                    // Extract diff from description
                    const diffMatch = description.match(/@@[\s\S]*$/);
                    const diff = diffMatch ? diffMatch[0] : null;

                    return {
                        date: new Date(pubDate),
                        link: link,
                        guid: guid,
                        diff: diff,
                        description: description
                    };
                }).sort((a, b) => b.date - a.date); // Sort newest first

            } catch (error) {
                console.error('Failed to load RSS feed:', error);
            }
        }

        createUI() {
            // Create date selector UI
            const selector = document.createElement('div');
            selector.id = 'history-selector';
            selector.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                background: white;
                border: 1px solid #ccc;
                padding: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                z-index: 1000;
                font-family: Arial, sans-serif;
            `;

            selector.innerHTML = `
                <h3 style="margin: 0 0 10px 0; font-size: 14px;">View History</h3>
                <select id="history-date-select" style="width: 200px; padding: 5px;">
                    <option value="">Current Version</option>
                    ${this.rssEntries.map((entry, index) => `
                        <option value="${entry.date.toISOString()}">
                            ${entry.date.toLocaleString()}
                        </option>
                    `).join('')}
                </select>
                <div id="history-status" style="margin-top: 10px; font-size: 12px; color: #666;"></div>
            `;

            document.body.appendChild(selector);

            // Add event listener
            const select = document.getElementById('history-date-select');
            select.addEventListener('change', async (e) => {
                const selectedDate = e.target.value;
                if (selectedDate) {
                    await this.reconstructVersion(selectedDate);
                    // Update URL
                    const url = new URL(window.location);
                    url.searchParams.set('date', selectedDate);
                    window.history.replaceState({}, '', url);
                } else {
                    // Show current version
                    document.body.innerHTML = this.currentContent;
                    document.body.appendChild(selector);
                    // Remove date from URL
                    const url = new URL(window.location);
                    url.searchParams.delete('date');
                    window.history.replaceState({}, '', url);
                }
            });
        }

        async reconstructVersion(targetDate) {
            const status = document.getElementById('history-status');
            if (status) {
                status.textContent = 'Reconstructing...';
            }

            try {
                const target = new Date(targetDate);
                let content = this.currentContent;

                // Find all entries newer than target date
                const newerEntries = this.rssEntries.filter(entry => entry.date > target);

                // Apply reverse diffs from newest to oldest
                for (const entry of newerEntries) {
                    if (entry.diff) {
                        content = this.applyReverseDiff(content, entry.diff);
                    }
                }

                // Update the page content
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = content;
                document.body.innerHTML = tempDiv.innerHTML;

                // Re-add the UI
                this.createUI();

                // Update the select to show current date
                const select = document.getElementById('history-date-select');
                if (select) {
                    select.value = targetDate;
                }

                if (status) {
                    status.textContent = `Showing version from ${target.toLocaleString()}`;
                }

            } catch (error) {
                console.error('Failed to reconstruct version:', error);
                if (status) {
                    status.textContent = 'Error reconstructing version';
                }
            }
        }

        applyReverseDiff(content, diff) {
            // Parse the unified diff format and apply it in reverse
            const lines = content.split('\n');
            const diffLines = diff.split('\n');
            let result = [...lines];

            // Process diff hunks
            let i = 0;
            while (i < diffLines.length) {
                const line = diffLines[i];

                // Look for hunk header
                if (line.startsWith('@@')) {
                    const match = line.match(/@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@/);
                    if (match) {
                        const oldStart = parseInt(match[1]) - 1;
                        const oldCount = parseInt(match[2] || '1');
                        const newStart = parseInt(match[3]) - 1;
                        const newCount = parseInt(match[4] || '1');

                        // Process the hunk
                        i++;
                        const hunkLines = [];
                        while (i < diffLines.length && !diffLines[i].startsWith('@@')) {
                            hunkLines.push(diffLines[i]);
                            i++;
                        }

                        // Apply hunk in reverse
                        result = this.applyReverseHunk(result, hunkLines, newStart);
                        continue;
                    }
                }
                i++;
            }

            return result.join('\n');
        }

        applyReverseHunk(lines, hunkLines, startLine) {
            const result = [...lines];
            let offset = 0;

            for (const hunkLine of hunkLines) {
                if (hunkLine.startsWith('+')) {
                    // In reverse, remove added lines
                    result.splice(startLine + offset, 1);
                    offset--;
                } else if (hunkLine.startsWith('-')) {
                    // In reverse, add removed lines
                    result.splice(startLine + offset, 0, hunkLine.substring(1));
                    offset++;
                }
                // Context lines (starting with space) are kept as-is
            }

            return result;
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            new HistoryViewer().init();
        });
    } else {
        new HistoryViewer().init();
    }
})();