/**
 * Address Autocomplete Component for Wheelchair Ride-Sharing
 * Provides accessible address input with real-time suggestions
 * Integrates with geocoding service and map component
 */

class AddressAutocomplete {
    constructor(inputElement, options = {}) {
        this.inputElement = inputElement;
        this.suggestionsContainer = null;
        this.currentSuggestions = [];
        this.selectedIndex = -1;
        this.isLoading = false;
        this.debounceTimer = null;
        
        // Configuration
        this.config = {
            minQueryLength: 2,
            debounceDelay: 300,
            maxSuggestions: 5,
            apiEndpoint: options.apiEndpoint || '/api',
            placeholder: options.placeholder || 'Enter address...',
            ariaLabel: options.ariaLabel || 'Address input with autocomplete',
            ...options
        };
        
        // Callbacks
        this.callbacks = {
            onSelect: options.onSelect || null,
            onError: options.onError || null,
            onLoading: options.onLoading || null
        };
        
        this.init();
    }
    
    /**
     * Initialize the autocomplete component
     */
    init() {
        this.setupInput();
        this.createSuggestionsContainer();
        this.attachEventListeners();
        this.addAccessibilityAttributes();
    }
    
    /**
     * Setup the input element
     */
    setupInput() {
        // Add CSS classes
        this.inputElement.classList.add('address-autocomplete-input');
        
        // Set attributes
        this.inputElement.setAttribute('autocomplete', 'off');
        this.inputElement.setAttribute('role', 'combobox');
        this.inputElement.setAttribute('aria-autocomplete', 'list');
        this.inputElement.setAttribute('aria-expanded', 'false');
        this.inputElement.setAttribute('aria-label', this.config.ariaLabel);
        
        if (this.config.placeholder) {
            this.inputElement.setAttribute('placeholder', this.config.placeholder);
        }
    }
    
    /**
     * Create suggestions container
     */
    createSuggestionsContainer() {
        this.suggestionsContainer = document.createElement('div');
        this.suggestionsContainer.className = 'address-suggestions';
        this.suggestionsContainer.setAttribute('role', 'listbox');
        this.suggestionsContainer.setAttribute('aria-label', 'Address suggestions');
        this.suggestionsContainer.style.display = 'none';
        
        // Insert after input element
        this.inputElement.parentNode.insertBefore(
            this.suggestionsContainer,
            this.inputElement.nextSibling
        );
        
        // Set ARIA relationship
        const suggestionsId = 'suggestions-' + Math.random().toString(36).substr(2, 9);
        this.suggestionsContainer.id = suggestionsId;
        this.inputElement.setAttribute('aria-owns', suggestionsId);
    }
    
    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Input events
        this.inputElement.addEventListener('input', (e) => {
            this.handleInput(e);
        });
        
        this.inputElement.addEventListener('keydown', (e) => {
            this.handleKeydown(e);
        });
        
        this.inputElement.addEventListener('focus', (e) => {
            this.handleFocus(e);
        });
        
        this.inputElement.addEventListener('blur', (e) => {
            this.handleBlur(e);
        });
        
        // Suggestions container events
        this.suggestionsContainer.addEventListener('click', (e) => {
            this.handleSuggestionClick(e);
        });
        
        // Close suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.inputElement.contains(e.target) && 
                !this.suggestionsContainer.contains(e.target)) {
                this.hideSuggestions();
            }
        });
    }
    
    /**
     * Add accessibility attributes
     */
    addAccessibilityAttributes() {
        // Create live region for screen readers
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        liveRegion.id = 'autocomplete-status-' + Math.random().toString(36).substr(2, 9);
        
        this.inputElement.parentNode.appendChild(liveRegion);
        this.statusRegion = liveRegion;
        
        // Set aria-describedby
        this.inputElement.setAttribute('aria-describedby', liveRegion.id);
    }
    
    /**
     * Handle input changes
     */
    handleInput(e) {
        const query = e.target.value.trim();
        
        // Clear existing timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Reset selection
        this.selectedIndex = -1;
        
        if (query.length < this.config.minQueryLength) {
            this.hideSuggestions();
            return;
        }
        
        // Debounce the search
        this.debounceTimer = setTimeout(() => {
            this.searchAddresses(query);
        }, this.config.debounceDelay);
    }
    
    /**
     * Handle keyboard navigation
     */
    handleKeydown(e) {
        const suggestions = this.suggestionsContainer.querySelectorAll('.suggestion-item');
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, suggestions.length - 1);
                this.updateSelection();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection();
                break;
                
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && suggestions[this.selectedIndex]) {
                    this.selectSuggestion(this.currentSuggestions[this.selectedIndex]);
                }
                break;
                
            case 'Escape':
                this.hideSuggestions();
                break;
                
            case 'Tab':
                // Allow tab to close suggestions
                this.hideSuggestions();
                break;
        }
    }
    
    /**
     * Handle input focus
     */
    handleFocus(e) {
        const query = e.target.value.trim();
        if (query.length >= this.config.minQueryLength && this.currentSuggestions.length > 0) {
            this.showSuggestions();
        }
    }
    
    /**
     * Handle input blur (with delay to allow for suggestion clicks)
     */
    handleBlur(e) {
        setTimeout(() => {
            if (document.activeElement !== this.suggestionsContainer &&
                !this.suggestionsContainer.contains(document.activeElement)) {
                this.hideSuggestions();
            }
        }, 150);
    }
    
    /**
     * Handle suggestion click
     */
    handleSuggestionClick(e) {
        const suggestionElement = e.target.closest('.suggestion-item');
        if (suggestionElement) {
            const index = parseInt(suggestionElement.dataset.index);
            const suggestion = this.currentSuggestions[index];
            if (suggestion) {
                this.selectSuggestion(suggestion);
            }
        }
    }
    
    /**
     * Search for addresses
     */
    async searchAddresses(query) {
        try {
            this.setLoading(true);
            
            // Use development public endpoint if available, fallback to authenticated
            const endpoint = this.config.suggestionsEndpoint || 
                            (this.config.usePublicEndpoint ? 
                             `${this.config.apiEndpoint}/geocoding/public/suggestions/` :
                             `${this.config.apiEndpoint}/geocoding/suggestions/`);
            
            const headers = {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            };
            
            // Add CSRF token if not using public endpoint
            if (!this.config.usePublicEndpoint) {
                headers['X-CSRFToken'] = this.getCSRFToken();
            }
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: headers,
                credentials: this.config.usePublicEndpoint ? 'omit' : 'same-origin',
                body: JSON.stringify({
                    query: query,
                    limit: this.config.maxSuggestions
                })
            });
            
            if (!response.ok) {
                if (response.status === 401 && !this.config.usePublicEndpoint) {
                    // Try public endpoint as fallback
                    return this.searchAddressesPublic(query);
                }
                throw new Error(`Search request failed: ${response.status}`);
            }
            
            const suggestions = await response.json();
            this.displaySuggestions(suggestions);
            
        } catch (error) {
            console.error('Address search error:', error);
            
            // Try fallback if main request failed
            if (!this.config.usePublicEndpoint) {
                try {
                    await this.searchAddressesPublic(query);
                    return;
                } catch (fallbackError) {
                    console.error('Fallback search also failed:', fallbackError);
                }
            }
            
            this.handleError('Failed to search addresses: ' + error.message);
            this.hideSuggestions();
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Fallback method using public endpoint
     */
    async searchAddressesPublic(query) {
        const response = await fetch(`${this.config.apiEndpoint}/geocoding/public/suggestions/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'omit',
            body: JSON.stringify({
                query: query,
                limit: this.config.maxSuggestions
            })
        });
        
        if (!response.ok) {
            throw new Error(`Public search failed: ${response.status}`);
        }
        
        const suggestions = await response.json();
        this.displaySuggestions(suggestions);
    }
    
    /**
     * Display suggestions
     */
    displaySuggestions(suggestions) {
        this.currentSuggestions = suggestions;
        this.selectedIndex = -1;
        
        if (suggestions.length === 0) {
            this.showNoResults();
            return;
        }
        
        // Clear existing suggestions
        this.suggestionsContainer.innerHTML = '';
        
        // Create suggestion elements
        suggestions.forEach((suggestion, index) => {
            const suggestionEl = this.createSuggestionElement(suggestion, index);
            this.suggestionsContainer.appendChild(suggestionEl);
        });
        
        this.showSuggestions();
        this.updateStatus(`${suggestions.length} suggestions available`);
    }
    
    /**
     * Create suggestion element
     */
    createSuggestionElement(suggestion, index) {
        const element = document.createElement('div');
        element.className = 'suggestion-item';
        element.setAttribute('role', 'option');
        element.setAttribute('data-index', index);
        element.setAttribute('tabindex', '-1');
        
        // Create suggestion content
        const content = document.createElement('div');
        content.className = 'suggestion-content';
        
        // Main address
        const mainAddress = document.createElement('div');
        mainAddress.className = 'suggestion-main';
        mainAddress.textContent = suggestion.formatted || suggestion.display_name;
        
        // Additional info
        const additionalInfo = document.createElement('div');
        additionalInfo.className = 'suggestion-details';
        
        // Add type icon and distance if available
        let details = [];
        if (suggestion.type) {
            details.push(this.getTypeIcon(suggestion.type) + ' ' + this.formatType(suggestion.type));
        }
        if (suggestion.distance_km) {
            details.push(`📏 ${suggestion.distance_km}km`);
        }
        
        additionalInfo.textContent = details.join(' • ');
        
        content.appendChild(mainAddress);
        if (details.length > 0) {
            content.appendChild(additionalInfo);
        }
        
        element.appendChild(content);
        
        // Add click handler
        element.addEventListener('click', () => {
            this.selectSuggestion(suggestion);
        });
        
        return element;
    }
    
    /**
     * Get icon for location type
     */
    getTypeIcon(type) {
        const iconMap = {
            'hospital': '🏥',
            'health_center': '⚕️',
            'pharmacy': '💊',
            'school': '🏫',
            'university': '🎓',
            'shopping': '🛒',
            'restaurant': '🍽️',
            'hotel': '🏨',
            'bank': '🏦',
            'post_office': '📮',
            'police': '👮',
            'fire_station': '🚒',
            'bus_stop': '🚌',
            'subway': '🚇',
            'airport': '✈️',
            'parking': '🅿️',
            'gas_station': '⛽',
            'road': '🛣️',
            'square': '🏛️',
            'park': '🌳'
        };
        
        return iconMap[type] || '📍';
    }
    
    /**
     * Format location type for display
     */
    formatType(type) {
        return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    /**
     * Show no results message
     */
    showNoResults() {
        this.suggestionsContainer.innerHTML = `
            <div class="suggestion-item no-results">
                <div class="suggestion-content">
                    <div class="suggestion-main">No addresses found</div>
                    <div class="suggestion-details">Try a different search term</div>
                </div>
            </div>
        `;
        
        this.showSuggestions();
        this.updateStatus('No addresses found');
    }
    
    /**
     * Show suggestions container
     */
    showSuggestions() {
        this.suggestionsContainer.style.display = 'block';
        this.inputElement.setAttribute('aria-expanded', 'true');
    }
    
    /**
     * Hide suggestions container
     */
    hideSuggestions() {
        this.suggestionsContainer.style.display = 'none';
        this.inputElement.setAttribute('aria-expanded', 'false');
        this.selectedIndex = -1;
    }
    
    /**
     * Update selection highlighting
     */
    updateSelection() {
        const suggestions = this.suggestionsContainer.querySelectorAll('.suggestion-item:not(.no-results)');
        
        suggestions.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
                item.setAttribute('aria-selected', 'true');
                
                // Update input with selected suggestion
                if (this.currentSuggestions[index]) {
                    this.updateStatus(`Selected: ${this.currentSuggestions[index].formatted}`);
                }
            } else {
                item.classList.remove('selected');
                item.setAttribute('aria-selected', 'false');
            }
        });
    }
    
    /**
     * Select a suggestion
     */
    selectSuggestion(suggestion) {
        // Update input value
        this.inputElement.value = suggestion.formatted || suggestion.display_name;
        
        // Hide suggestions
        this.hideSuggestions();
        
        // Call callback
        if (this.callbacks.onSelect) {
            this.callbacks.onSelect(suggestion);
        }
        
        // Update status
        this.updateStatus(`Selected: ${suggestion.formatted || suggestion.display_name}`);
    }
    
    /**
     * Set loading state
     */
    setLoading(isLoading) {
        this.isLoading = isLoading;
        
        if (isLoading) {
            this.inputElement.classList.add('loading');
            this.showLoadingIndicator();
            
            if (this.callbacks.onLoading) {
                this.callbacks.onLoading(true);
            }
        } else {
            this.inputElement.classList.remove('loading');
            
            if (this.callbacks.onLoading) {
                this.callbacks.onLoading(false);
            }
        }
    }
    
    /**
     * Show loading indicator
     */
    showLoadingIndicator() {
        this.suggestionsContainer.innerHTML = `
            <div class="suggestion-item loading-item">
                <div class="suggestion-content">
                    <div class="suggestion-main">
                        <span class="loading-spinner">⏳</span> Searching addresses...
                    </div>
                </div>
            </div>
        `;
        this.showSuggestions();
    }
    
    /**
     * Update status for screen readers
     */
    updateStatus(message) {
        if (this.statusRegion) {
            this.statusRegion.textContent = message;
        }
    }
    
    /**
     * Handle errors
     */
    handleError(message) {
        console.error('Autocomplete Error:', message);
        this.updateStatus('Error searching addresses');
        
        if (this.callbacks.onError) {
            this.callbacks.onError(message);
        }
    }
    
    /**
     * Get CSRF token for API requests
     */
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        // Fallback to meta tag
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    /**
     * Clear the input and suggestions
     */
    clear() {
        this.inputElement.value = '';
        this.hideSuggestions();
        this.currentSuggestions = [];
        this.updateStatus('Input cleared');
    }
    
    /**
     * Set the input value programmatically
     */
    setValue(value) {
        this.inputElement.value = value;
        this.hideSuggestions();
    }
    
    /**
     * Get current input value
     */
    getValue() {
        return this.inputElement.value;
    }
    
    /**
     * Enable/disable the input
     */
    setEnabled(enabled) {
        this.inputElement.disabled = !enabled;
        
        if (!enabled) {
            this.hideSuggestions();
        }
    }
    
    /**
     * Destroy the autocomplete component
     */
    destroy() {
        // Remove event listeners
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Remove DOM elements
        if (this.suggestionsContainer && this.suggestionsContainer.parentNode) {
            this.suggestionsContainer.parentNode.removeChild(this.suggestionsContainer);
        }
        
        if (this.statusRegion && this.statusRegion.parentNode) {
            this.statusRegion.parentNode.removeChild(this.statusRegion);
        }
        
        // Clean up input element
        this.inputElement.classList.remove('address-autocomplete-input', 'loading');
        this.inputElement.removeAttribute('role');
        this.inputElement.removeAttribute('aria-autocomplete');
        this.inputElement.removeAttribute('aria-expanded');
        this.inputElement.removeAttribute('aria-owns');
        this.inputElement.removeAttribute('aria-describedby');
    }
}

/**
 * Utility function to initialize autocomplete on multiple inputs
 */
function initializeAddressAutocomplete(selector, options = {}) {
    const inputs = document.querySelectorAll(selector);
    const instances = [];
    
    inputs.forEach(input => {
        const instance = new AddressAutocomplete(input, options);
        instances.push(instance);
    });
    
    return instances;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AddressAutocomplete, initializeAddressAutocomplete };
}