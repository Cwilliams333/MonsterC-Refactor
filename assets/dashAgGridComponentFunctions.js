/**
 * Custom cell renderers for Dash AG Grid
 * Enables clickable collapsible test case groups in Community Edition
 */

// Initialize the global namespace for Dash AG Grid component functions
window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {};

/**
 * Clickable hierarchy renderer for test case collapse/expand functionality
 */
window.dashAgGridComponentFunctions.clickableHierarchyRenderer = function(props) {
    const { value, data, setProps } = props;

    // Check if this is a group row (test case header like "📁 Camera Pictures")
    const isGroup = data && data.isGroup && !data.isTotal;
    const isTotal = data && data.isTotal;

    if (isGroup) {
        // This is a test case header - make it clickable!
        return React.createElement(
            'div',
            {
                onClick: () => {
                    // Send click data back to Dash
                    const testCaseName = value.replace('📁 ', ''); // Remove folder icon
                    setProps({
                        cellRendererData: {
                            action: 'toggle_group',
                            testCase: testCaseName,
                            timestamp: Date.now() // Force update
                        }
                    });
                },
                style: {
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    padding: '5px',
                    userSelect: 'none',
                    color: '#ffffff', // White text for dark background
                    backgroundColor: '#495057', // Keep existing dark background
                    borderRadius: '3px',
                    transition: 'background-color 0.2s ease'
                },
                onMouseOver: (e) => {
                    e.target.style.backgroundColor = '#6c757d'; // Lighter on hover
                },
                onMouseOut: (e) => {
                    e.target.style.backgroundColor = '#495057'; // Back to original
                },
                title: 'Click to collapse/expand models'
            },
            [
                React.createElement('span', { style: { marginRight: '5px' } }, '🔽'), // Down arrow when expanded
                value.replace('📁', '📁') // Keep the folder icon
            ]
        );
    } else if (isTotal) {
        // Total row - not clickable but styled
        return React.createElement(
            'div',
            {
                style: {
                    fontWeight: 'bold',
                    color: '#ffffff',
                    backgroundColor: '#17a2b8', // Blue background for total
                    padding: '5px',
                    borderRadius: '3px'
                }
            },
            value
        );
    } else {
        // Model row - just show the value with indentation
        return React.createElement(
            'div',
            {
                style: {
                    paddingLeft: '30px',
                    color: '#6c757d',
                    fontStyle: 'italic'
                }
            },
            value
        );
    }
};

// Export the component functions
var dagcomponentfuncs = window.dashAgGridComponentFunctions;

// Log successful registration
console.log('✅ Dash AG Grid custom cell renderers loaded:', Object.keys(window.dashAgGridComponentFunctions));

// Verify the component is properly accessible
if (window.dashAgGridComponentFunctions.clickableHierarchyRenderer) {
    console.log('✅ clickableHierarchyRenderer registered successfully');
} else {
    console.error('❌ clickableHierarchyRenderer failed to register');
}
