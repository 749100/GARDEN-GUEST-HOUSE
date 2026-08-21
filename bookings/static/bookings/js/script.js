document.addEventListener('DOMContentLoaded', () => {

    // =========================================================================
    // 1. UNIVERSAL NAVIGATION DRAWER & ADVANCED ACCORDION ENGINE
    // =========================================================================
    const menuToggle = document.querySelector('.mobile-menu-toggle');
    const closeToggle = document.querySelector('.drawer-close-trigger');
    const navigationDrawer = document.querySelector('.header-left nav');
    const dropdownContainers = document.querySelectorAll('.has-dropdown');

    if (menuToggle && navigationDrawer) {
        
        // Open Mobile Canvas Drawer Layer
        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            navigationDrawer.classList.add('active');
        });

        // Hide Mobile Canvas Drawer via Close Trigger 'X'
        if (closeToggle) {
            closeToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                navigationDrawer.classList.remove('active');
            });
        }

        // Hide Mobile Canvas Drawer when clicking out onto the blurred backdrop overlay
        navigationDrawer.addEventListener('click', (e) => {
            if (e.target === navigationDrawer) {
                navigationDrawer.classList.remove('active');
            }
        });

        // HANDLE UNIVERSAL ACCORDION TRIGGERS (Operational on all viewports)
        dropdownContainers.forEach(container => {
            const toggleBtn = container.querySelector('.dropdown-toggle-btn');
            const primaryLink = container.querySelector('.menu-link-wrapper > a');
            
            const handleDropdownToggle = (e) => {
                // Intercept clicks on all screen sizes now that the toggle button is global
                e.preventDefault(); 
                e.stopPropagation();
                
                // Collapse sibling open trays to prevent multi-panel vertical overlaps
                dropdownContainers.forEach(other => {
                    if (other !== container && !container.contains(other)) {
                        other.classList.remove('open');
                    }
                });

                // Toggle visibility layer state tokens
                container.classList.toggle('open');
            };

            // Bind click listeners cleanly to both the text segment and geometric plus button icon
            if (toggleBtn) toggleBtn.addEventListener('click', handleDropdownToggle);
            if (primaryLink) primaryLink.addEventListener('click', handleDropdownToggle);
        });

        // AUTO-DISMISS CORE DRAWER SYSTEM WHEN SELECTION END LINKS ARE EXECUTED
        const leafLinks = navigationDrawer.querySelectorAll('a');
        leafLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // If it's just an internal placeholder link, ignore and let the dropdown toggle take over
                if (link.getAttribute('href') === '#') {
                    return;
                }
                
                // For functional page links (like Django's /about/), dismiss layout state components cleanly
                navigationDrawer.classList.remove('active');
                dropdownContainers.forEach(c => c.classList.remove('open'));
            });
        });

        // GLOBAL CLICK-AWAY RESET DISMISSAL: Closes active menus when user clicks regular whitespace
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.header-left')) {
                dropdownContainers.forEach(container => {
                    container.classList.remove('open');
                });
            }
        });
    }

    // =========================================================================
    // 2. ACCOMMODATION SELECTION ARCHITECTURE
    // =========================================================================
    const selectButtons = document.querySelectorAll('.select-link-btn');
    const roomCards = document.querySelectorAll('.room-card-premium');

    if (selectButtons.length > 0 && roomCards.length > 0) {
        selectButtons.forEach((button, index) => {
            button.addEventListener('click', (event) => {
                // event.preventDefault() removed so the anchor links can fire natively!

                const targetCard = roomCards[index];
                if (!targetCard) return;

                // Reset sibling layout card styling back to premium dark architecture defaults
                roomCards.forEach(card => {
                    card.style.border = 'none';
                    card.style.boxShadow = '0 15px 35px rgba(0,0,0,0.3)';
                });
                selectButtons.forEach(btn => {
                    btn.innerHTML = 'Select Room →';
                    btn.style.color = 'var(--primary)';
                });

                // Apply premium gold structural highlights onto selected room card container asset
                targetCard.style.transition = 'all 0.4s cubic-bezier(0.25, 1, 0.5, 1)';
                targetCard.style.border = '1px solid var(--primary)';
                targetCard.style.boxShadow = '0 0 30px rgba(197, 168, 128, 0.35)';
                
                button.innerHTML = 'Selected Luxury ✓';
                button.style.color = '#fff';
            });
        });
    }
});