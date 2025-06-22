/**
 * Simple clickable groups implementation for AG Grid
 * Alternative approach using event delegation
 */

console.log('🔄 Loading clickable groups JavaScript...');

// Wait for AG Grid to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM loaded, setting up clickable groups...');

    // Add CSS for clickable cursor
    const style = document.createElement('style');
    style.textContent = `
        .ag-cell[col-id="hierarchy"] .group-row {
            cursor: pointer !important;
            transition: background-color 0.2s ease;
        }
        .ag-cell[col-id="hierarchy"] .group-row:hover {
            background-color: #6c757d !important;
        }
        .clickable-test-case {
            cursor: pointer !important;
            user-select: none;
        }
    `;
    document.head.appendChild(style);

    // Use MutationObserver to detect when AG Grid is rendered
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                setupClickHandlers();
            }
        });
    });

    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Initial setup
    setTimeout(setupClickHandlers, 1000);
});

function setupClickHandlers() {
    // Find AG Grid hierarchy column cells
    const hierarchyCells = document.querySelectorAll('.ag-cell[col-id="hierarchy"]');

    hierarchyCells.forEach(function(cell) {
        const cellText = cell.textContent || '';

        // Check if this is a test case header (contains 📁 but not 📊 or └─)
        if (cellText.includes('📁') && !cellText.includes('📊') && !cellText.includes('└─')) {
            console.log('🎯 Found test case header:', cellText);

            // Add clickable styling
            cell.style.cursor = 'pointer';
            cell.title = 'Click to collapse/expand models';

            // Remove existing click listeners to avoid duplicates
            cell.onclick = null;

            // Add click handler
            cell.onclick = function(event) {
                event.preventDefault();
                event.stopPropagation();

                const testCaseName = cellText.replace('📁 ', '').trim();
                console.log('🔽 Clicked test case:', testCaseName);

                // Find the Dash component and trigger a callback
                const gridElement = cell.closest('.ag-root-wrapper');
                if (gridElement && gridElement._dashRendered && gridElement._dashRendered.props) {
                    const dashProps = gridElement._dashRendered.props;
                    if (dashProps.setProps) {
                        dashProps.setProps({
                            cellRendererData: {
                                action: 'toggle_group',
                                testCase: testCaseName,
                                timestamp: Date.now()
                            }
                        });
                        console.log('✅ Sent toggle event to Dash:', testCaseName);
                    } else {
                        console.warn('⚠️ setProps not found on Dash component');
                    }
                } else {
                    console.warn('⚠️ Could not find Dash component');
                }
            };

            // Add hover effects
            cell.onmouseenter = function() {
                if (cell.style.backgroundColor !== '#6c757d') {
                    cell.dataset.originalBg = cell.style.backgroundColor;
                    cell.style.backgroundColor = '#6c757d';
                }
            };

            cell.onmouseleave = function() {
                if (cell.dataset.originalBg !== undefined) {
                    cell.style.backgroundColor = cell.dataset.originalBg;
                    delete cell.dataset.originalBg;
                }
            };
        }
    });

    console.log(`🎯 Set up click handlers for ${hierarchyCells.length} hierarchy cells`);
}

console.log('✅ Clickable groups JavaScript loaded');
