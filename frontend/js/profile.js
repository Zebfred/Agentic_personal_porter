/**
 * Profile page logic.
 * Handles fetching user profile and accepting/declining Guild Invitations.
 */

document.addEventListener('DOMContentLoaded', async () => {
    Auth.enforceAuth();

    const loadingDiv = document.getElementById('profile-loading');
    const contentDiv = document.getElementById('profile-content');
    
    // Profile Elements
    const nameEl = document.getElementById('profile-name');
    const emailEl = document.getElementById('profile-email');
    const picEl = document.getElementById('profile-picture');
    const roleBadge = document.getElementById('role-badge');
    
    // Guild Elements
    const inviteBanner = document.getElementById('guild-invitation');
    const statusMessage = document.getElementById('guild-status-message');
    const btnAccept = document.getElementById('btn-accept-invite');
    const btnDecline = document.getElementById('btn-decline-invite');

    try {
        const response = await fetch('/api/user/profile', {
            headers: {
                'Authorization': `Bearer ${Auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to fetch profile');

        const data = await response.json();
        const profile = data.profile || {};
        
        // Populate info
        nameEl.textContent = profile.name || 'Unknown Hero';
        emailEl.textContent = data.email;
        if (profile.picture) {
            picEl.src = profile.picture;
        }

        // Setup Role Badge
        if (data.role === 'admin' || data.role === 'guild_member') {
            roleBadge.textContent = 'Nexus Guild Member';
            roleBadge.className = 'inline-block px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-semibold tracking-wide uppercase';
        } else {
            roleBadge.textContent = 'Hero';
        }

        // Setup Guild Invitation UI
        if (data.guild_invite_status === 'pending') {
            inviteBanner.classList.remove('hidden');
        } else if (data.guild_invite_status === 'accepted' || data.guild_invite_status === 'admin') {
            statusMessage.classList.remove('hidden');
        }

        // Hide loading, show content
        loadingDiv.classList.add('hidden');
        contentDiv.classList.remove('hidden');

        // Setup Analytics Toggle
        const analyticsToggle = document.getElementById('analytics-toggle');
        const analyticsBg = document.getElementById('analytics-bg');
        const analyticsDot = document.getElementById('analytics-dot');
        const analyticsMsg = document.getElementById('analytics-status-msg');

        const updateToggleUI = (isOptedIn) => {
            if (isOptedIn) {
                analyticsBg.classList.replace('bg-gray-300', 'bg-blue-500');
                analyticsDot.classList.add('translate-x-6');
            } else {
                analyticsBg.classList.replace('bg-blue-500', 'bg-gray-300');
                analyticsDot.classList.remove('translate-x-6');
            }
        };

        // Initial state
        analyticsToggle.checked = data.privacy_opt_in_analytics === true;
        updateToggleUI(analyticsToggle.checked);

        analyticsToggle.addEventListener('change', async (e) => {
            const isOptedIn = e.target.checked;
            updateToggleUI(isOptedIn);
            analyticsMsg.classList.add('hidden');

            try {
                const optInRes = await fetch('/api/user/opt_in_analytics', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${Auth.getToken()}`
                    },
                    body: JSON.stringify({ opt_in: isOptedIn })
                });

                if (!optInRes.ok) throw new Error('Failed to update preferences');
                
                analyticsMsg.textContent = isOptedIn ? "✅ Opted in to share telemetry." : "✅ Opted out of sharing telemetry.";
                analyticsMsg.className = "mt-3 text-sm font-medium text-green-600 transition-opacity";
            } catch (err) {
                console.error("Toggle error:", err);
                analyticsMsg.textContent = "❌ Failed to save preference. Please try again.";
                analyticsMsg.className = "mt-3 text-sm font-medium text-red-600 transition-opacity";
                // Revert UI on failure
                e.target.checked = !isOptedIn;
                updateToggleUI(!isOptedIn);
            }
        });

    } catch (error) {
        console.error("Error loading profile:", error);
        loadingDiv.innerHTML = `<p class="text-red-500 font-bold">Error loading profile data. Please try logging in again.</p>`;
    }

    // Handle Invite Actions
    const handleInviteAction = async (action) => {
        try {
            // Disable buttons during request
            btnAccept.disabled = true;
            btnDecline.disabled = true;

            const response = await fetch('/api/user/invite', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${Auth.getToken()}`
                },
                body: JSON.stringify({ action })
            });

            if (!response.ok) throw new Error('Failed to update invitation status');

            const result = await response.json();
            
            // Hide banner
            inviteBanner.classList.add('hidden');
            
            if (action === 'accept') {
                alert("Welcome to the Nexus Guild! Please log in again to refresh your privileges.");
                Auth.logout(); // Force re-login to get the new JWT role
            } else {
                alert("Invitation declined. You can continue using standard Hero features.");
            }

        } catch (error) {
            console.error("Action error:", error);
            alert("An error occurred. Please try again.");
            btnAccept.disabled = false;
            btnDecline.disabled = false;
        }
    };

    btnAccept.addEventListener('click', () => handleInviteAction('accept'));
    btnDecline.addEventListener('click', () => handleInviteAction('decline'));
});
