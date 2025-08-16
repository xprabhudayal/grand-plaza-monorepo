// Global variables
let dailyCall = null;
let currentOrder = [];
let menuItems = [];

// DOM Elements
const startCallBtn = document.getElementById('start-call-btn');
const videoContainer = document.getElementById('video-call-container');
const callStatus = document.getElementById('call-status');
const menuContainer = document.getElementById('menu-container');
const menuItemsContainer = document.getElementById('menu-items');
const loadingMenu = document.getElementById('loading-menu');
const clearOrderBtn = document.getElementById('clear-order-btn');
const placeOrderBtn = document.getElementById('place-order-btn');
const toastContainer = document.getElementById('toast-container');

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    loadMenuItems();
});

startCallBtn.addEventListener('click', () => {
    if (dailyCall) {
        endVoiceCall();
    } else {
        startVoiceCall();
    }
});
clearOrderBtn.addEventListener('click', clearOrder);
placeOrderBtn.addEventListener('click', placeOrder);

// Load menu items from API
async function loadMenuItems() {
    try {
        const response = await fetch('/api/v1/menu-items/');
        if (!response.ok) throw new Error('Failed to load menu items');
        
        menuItems = await response.json();
        displayMenuItems();
    } catch (error) {
        console.error('Error loading menu:', error);
        showToast('Failed to load menu items', 'error');
        loadingMenu.innerHTML = '<p class="text-error text-center">Failed to load menu</p>';
    }
}

// Display menu items
function displayMenuItems() {
    loadingMenu.classList.add('hidden');
    menuItemsContainer.classList.remove('hidden');
    menuItemsContainer.className = 'grid grid-cols-1 md:grid-cols-2 gap-4';
    
    menuItemsContainer.innerHTML = '';
    
    menuItems.forEach(item => {
        const menuItemCard = document.createElement('div');
        menuItemCard.className = 'menu-item-card card bg-base-200 hover:bg-base-300 cursor-pointer';
        menuItemCard.innerHTML = `
            <div class="card-body p-4">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="font-bold text-lg">${item.name}</h3>
                        <p class="text-sm text-base-content/70 mt-1">${item.description}</p>
                    </div>
                    <span class="font-bold text-primary">$${item.price.toFixed(2)}</span>
                </div>
                <div class="card-actions justify-end mt-3">
                    <button class="add-to-order-btn btn btn-sm btn-primary" data-item-id="${item.id}">
                        Add to Order
                    </button>
                </div>
            </div>
        `;
        menuItemsContainer.appendChild(menuItemCard);
    });
    
    // Add event listeners to "Add to Order" buttons
    document.querySelectorAll('.add-to-order-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const itemId = e.target.dataset.itemId;
            addToOrder(itemId);
        });
    });
}

// Add item to order
function addToOrder(itemId) {
    const item = menuItems.find(i => i.id === itemId);
    if (!item) return;
    
    // Check if item is already in order
    const existingItem = currentOrder.find(i => i.id === itemId);
    if (existingItem) {
        existingItem.quantity += 1;
        showToast(`${item.name} quantity increased to ${existingItem.quantity}`, 'success');
    } else {
        currentOrder.push({
            ...item,
            quantity: 1
        });
        showToast(`${item.name} added to order`, 'success');
    }
    
    updateOrderDisplay();
}

// Update order display
function updateOrderDisplay() {
    // Enable or disable the place order button based on whether there are items in the order
    if (currentOrder.length === 0) {
        placeOrderBtn.disabled = true;
    } else {
        placeOrderBtn.disabled = false;
    }
}



// Clear order
function clearOrder() {
    currentOrder = [];
    updateOrderDisplay();
    showToast('Order cleared', 'info');
}

// Place order
async function placeOrder() {
    if (currentOrder.length === 0) {
        showToast('Please add items to your order first', 'warning');
        return;
    }
    
    try {
        // Create order data
        const orderData = {
            guest_id: "sample_guest_id", // In a real app, this would be dynamically set
            special_requests: "",
            delivery_notes: "Room 101",
            order_items: currentOrder.map(item => ({
                menu_item_id: item.id,
                quantity: item.quantity,
                special_notes: ""
            }))
        };
        
        // Send order to API
        const response = await fetch('/api/v1/orders/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(orderData)
        });
        
        if (!response.ok) throw new Error('Failed to place order');
        
        const order = await response.json();
        console.log('Order placed:', order);
        
        // Show success toast
        showToast(`Order placed successfully! Total: $${order.total_amount.toFixed(2)}`, 'success');
        
        // Clear order
        currentOrder = [];
        updateOrderDisplay();
        
    } catch (error) {
        console.error('Error placing order:', error);
        showToast('Failed to place order. Please try again.', 'error');
    }
}

// Start voice call
async function startVoiceCall() {
    try {
        // If there's already a call, clean it up first
        if (dailyCall) {
            dailyCall.destroy();
            dailyCall = null;
        }

        startCallBtn.disabled = true;
        startCallBtn.textContent = 'Starting...';
        callStatus.classList.remove('hidden');
        callStatus.textContent = 'Initializing call...';
        
        // Call the backend API to start the voice call
        const response = await fetch('/api/v1/voice-sessions/start-call?room_number=101', {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Failed to start voice call');
        
        
        const session = await response.json();
        console.log('Backend session started:', session);

        // --- Start of Daily.co Integration ---

        // 1. Clear the placeholder content
        videoContainer.innerHTML = ''; 

        // 2. Create the Daily.co call frame with proper containment
        const callFrame = Daily.createFrame(videoContainer, {
            showLeaveButton: true,
            iframeStyle: {
                position: 'relative',
                width: '100%',
                height: '100%',
                border: '0',
                borderRadius: '0.5rem',
                maxWidth: '100%',
                maxHeight: '100%',
                overflow: 'hidden'
            },
            layoutConfig: {
                grid: {
                    maxTilesPerPage: 4,
                    minTilesPerPage: 1
                }
            }
        });

        // 3. Join the call using your Daily.co room URL
        await callFrame.join({ url: 'https://pdv.daily.co/Grand-Plaza-Hotel-Service' });

        // 4. Store the call frame reference for cleanup
        dailyCall = callFrame;

        // 5. Add event listeners for call events
        callFrame.on('left-meeting', () => {
            callStatus.textContent = 'Call ended';
            startCallBtn.disabled = false;
            startCallBtn.textContent = 'Start Voice Call';
            dailyCall = null;
        });

        callFrame.on('error', (error) => {
            console.error('Daily.co error:', error);
            callStatus.textContent = 'Call error occurred';
            showToast('Call error occurred', 'error');
            startCallBtn.disabled = false;
            startCallBtn.textContent = 'Start Voice Call';
        });

        // --- End of Daily.co Integration ---

        callStatus.textContent = 'Call is active!';
        startCallBtn.textContent = 'End Call';
        startCallBtn.disabled = false;
        showToast('Voice call started', 'success');
        
    } catch (error) {
        console.error('Error starting voice call:', error);
        callStatus.textContent = 'Failed to start call';
        showToast('Failed to start voice call', 'error');
        startCallBtn.disabled = false;
        startCallBtn.textContent = 'Start Voice Call';
    }
}

// End voice call
function endVoiceCall() {
    if (dailyCall) {
        dailyCall.leave();
        dailyCall.destroy();
        dailyCall = null;
    }
    
    // Reset the video container
    videoContainer.innerHTML = `
        <div class="text-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mx-auto text-base-content/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <p class="mt-2 text-base-content/50">Video call will appear here</p>
        </div>
    `;
    
    startCallBtn.textContent = 'Start Voice Call';
    startCallBtn.disabled = false;
    callStatus.textContent = 'Call ended';
    
    showToast('Voice call ended', 'info');
}


// Show toast notification
function showToast(message, type = 'info') {
    // Remove any existing toasts
    toastContainer.innerHTML = '';
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} shadow-lg`;
    
    // Set toast content based on type
    let icon = '';
    switch(type) {
        case 'success':
            icon = '<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>';
            break;
        case 'error':
            icon = '<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>';
            break;
        case 'warning':
            icon = '<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>';
            break;
        default:
            icon = '<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>';
    }
    
    toast.innerHTML = `
        <div>
            ${icon}
            <span>${message}</span>
        </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (toastContainer.contains(toast)) {
            toastContainer.removeChild(toast);
        }
    }, 3000);
}