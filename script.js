(() => {
  'use strict';

  // Initialize icons
  lucide.createIcons();

  // API Base URL
  const API_BASE = 'http://localhost:5000/api';

  // DOM refs
  const DOM = {
    form: document.getElementById('addCropForm'),
    cropName: document.getElementById('cropName'),
    cropQty: document.getElementById('cropQty'),
    cropPrice: document.getElementById('cropPrice'),
    btnAdd: document.getElementById('btnAdd'),
    btnReset: document.getElementById('btnReset'),
    formError: document.getElementById('formError'),
    cropTbody: document.getElementById('cropTbody'),
    cropsCount: document.getElementById('cropsCount'),
    ordersTbody: document.getElementById('ordersTbody'),
    ordersCount: document.getElementById('ordersCount'),
    btnClearStorage: document.getElementById('btnClearStorage'),
    btnImportSample: document.getElementById('btnImportSample'),
    btnAddSampleOrder: document.getElementById('btnAddSampleOrder'),
    globalSearch: document.getElementById('globalSearch'),
    clearSearch: document.getElementById('clearSearch'),
    statusFilter: document.getElementById('statusFilter'),
    sortBy: document.getElementById('sortBy')
  };

  // State
  let state = {
    crops: [],
    orders: []
  };

  // Utilities
  const utils = {
    fetchAPI: async (endpoint, method = 'GET', body = null) => {
      try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: body ? JSON.stringify(body) : null
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        return await response.json();
      } catch (e) {
        throw new Error(`API error at ${endpoint}: ${e.message}`);
      }
    },
    escapeHtml: (s) => {
      if (!s && s !== 0) return '';
      return String(s).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m]);
    },
    debounce: (fn, delay) => {
      let timeout;
      return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
      };
    }
  };

  // Render functions
  const render = {
    crops: () => {
      try {
        const q = DOM.globalSearch.value.trim().toLowerCase();
        const status = DOM.statusFilter.value;
        let list = [...state.crops];

        if (status !== 'all') list = list.filter(c => c.status === status);
        if (q) {
          list = list.filter(c => 
            c.name.toLowerCase().includes(q) ||
            (c.note && c.note.toLowerCase().includes(q))
          );
        }

        const s = DOM.sortBy.value;
        if (s === 'qty-desc') list.sort((a, b) => b.quantity - a.quantity);
        else if (s === 'qty-asc') list.sort((a, b) => a.quantity - b.quantity);
        else if (s === 'price-desc') list.sort((a, b) => b.price - a.price);
        else if (s === 'price-asc') list.sort((a, b) => a.price - b.price);

        DOM.cropsCount.textContent = list.length;
        DOM.cropTbody.innerHTML = list.length === 0
          ? '<tr><td colspan="5" class="px-4 py-4 text-center text-gray-500">No crops found.</td></tr>'
          : list.map(c => `
              <tr data-id="${c.id}" class="hover:bg-gray-50">
                <td class="px-4 py-2 border-b">
                  <div class="font-medium">${utils.escapeHtml(c.name)}</div>
                  <div class="text-xs text-gray-500 mt-1">${c.note ? utils.escapeHtml(c.note) : ''}</div>
                </td>
                <td class="text-center px-4 py-2 border-b">${Number(c.quantity).toLocaleString()}</td>
                <td class="text-center px-4 py-2 border-b">₹${Number(c.price).toLocaleString()}</td>
                <td class="text-center px-4 py-2 border-b">
                  <select class="status-select border rounded px-2 py-1" data-id="${c.id}" aria-label="Change status">
                    <option value="Available" ${c.status === 'Available' ? 'selected' : ''}>Available</option>
                    <option value="Sold Out" ${c.status === 'Sold Out' ? 'selected' : ''}>Sold Out</option>
                  </select>
                </td>
                <td class="text-center px-4 py-2 border-b">
                  <button class="edit-btn px-2 py-1 mr-1 text-sm rounded border" data-edit="${c.id}" title="Edit">Edit</button>
                  <button class="delete-btn px-2 py-1 text-sm rounded border text-red-600" data-delete="${c.id}" title="Delete">Delete</button>
                </td>
              </tr>
            `).join('');

        lucide.createIcons();
      } catch (e) {
        console.error('Error rendering crops:', e);
        DOM.cropTbody.innerHTML = '<tr><td colspan="5" class="px-4 py-4 text-center text-red-600 error-boundary">Error rendering crops. Please try again.</td></tr>';
      }
    },
    orders: () => {
      try {
        const q = DOM.globalSearch.value.trim().toLowerCase();
        let list = [...state.orders];

        if (q) {
          list = list.filter(o =>
            o.buyer.toLowerCase().includes(q) ||
            o.product.toLowerCase().includes(q) ||
            String(o.id).includes(q)
          );
        }

        DOM.ordersCount.textContent = list.length;
        DOM.ordersTbody.innerHTML = list.length === 0
          ? '<tr><td colspan="6" class="px-4 py-4 text-center text-gray-500">No orders yet.</td></tr>'
          : list.map(o => `
              <tr data-id="${o.id}" class="hover:bg-gray-50">
                <td class="px-4 py-2 border-b">${o.id}</td>
                <td class="px-4 py-2 border-b">${utils.escapeHtml(o.buyer)}</td>
                <td class="px-4 py-2 border-b">${utils.escapeHtml(o.product)}</td>
                <td class="text-center px-4 py-2 border-b">${Number(o.qty).toLocaleString()}</td>
                <td class="text-center px-4 py-2 border-b">
                  <select class="order-status-select border rounded px-2 py-1" data-id="${o.id}">
                    <option value="Received" ${o.status === 'Received' ? 'selected' : ''}>Received</option>
                    <option value="Processing" ${o.status === 'Processing' ? 'selected' : ''}>Processing</option>
                    <option value="Dispatched" ${o.status === 'Dispatched' ? 'selected' : ''}>Dispatched</option>
                    <option value="Delivered" ${o.status === 'Delivered' ? 'selected' : ''}>Delivered</option>
                  </select>
                </td>
                <td class="text-center px-4 py-2 border-b">
                  <button class="delete-order-btn px-2 py-1 text-sm rounded border text-red-600" data-delete-order="${o.id}" title="Delete order">Delete</button>
                </td>
              </tr>
            `).join('');

        lucide.createIcons();
      } catch (e) {
        console.error('Error rendering orders:', e);
        DOM.ordersTbody.innerHTML = '<tr><td colspan="6" class="px-4 py-4 text-center text-red-600 error-boundary">Error rendering orders. Please try again.</td></tr>';
      }
    }
  };

  // Event handlers
  const handlers = {
    validateForm: () => {
      const name = DOM.cropName.value.trim();
      const qty = Number(DOM.cropQty.value);
      const price = Number(DOM.cropPrice.value);
      const isValid = name && qty > 0 && price > 0;
      DOM.btnAdd.disabled = !isValid;
      DOM.formError.textContent = isValid ? '' : 'Please provide valid name, quantity, and price.';
      DOM.formError.classList.toggle('hidden', isValid);
    },
    addCrop: async (ev) => {
      ev.preventDefault();
      try {
        const name = DOM.cropName.value.trim();
        const qty = Number(DOM.cropQty.value);
        const price = Number(DOM.cropPrice.value);

        if (!name || qty <= 0 || price <= 0) {
          DOM.formError.textContent = 'Invalid input values.';
          DOM.formError.classList.remove('hidden');
          return;
        }

        const crop = await utils.fetchAPI('/crops', 'POST', { name, quantity: qty, price });
        state.crops.unshift(crop);
        render.crops();
        DOM.form.reset();
        DOM.btnAdd.disabled = true;
      } catch (e) {
        console.error('Error adding crop:', e);
        DOM.formError.textContent = 'Error adding crop. Please try again.';
        DOM.formError.classList.remove('hidden');
      }
    },
    resetForm: () => {
      DOM.form.reset();
      DOM.formError.textContent = '';
      DOM.formError.classList.add('hidden');
      DOM.btnAdd.disabled = true;
    },
    updateCropStatus: async (ev) => {
      if (ev.target.classList.contains('status-select')) {
        try {
          const id = ev.target.dataset.id;
          const crop = state.crops.find(c => c.id === id);
          if (crop) {
            crop.status = ev.target.value;
            await utils.fetchAPI(`/crops/${id}`, 'PUT', { status: crop.status });
            render.crops();
          }
        } catch (e) {
          console.error('Error updating crop status:', e);
        }
      }
    },
    handleCropActions: async (ev) => {
      try {
        const deleteBtn = ev.target.closest('[data-delete]');
        if (deleteBtn) {
          const id = deleteBtn.dataset.delete;
          if (confirm('Delete this crop? This action cannot be undone.')) {
            await utils.fetchAPI(`/crops/${id}`, 'DELETE');
            state.crops = state.crops.filter(c => c.id !== id);
            render.crops();
          }
          return;
        }

        const editBtn = ev.target.closest('[data-edit]');
        if (editBtn) {
          const id = editBtn.dataset.edit;
          const crop = state.crops.find(c => c.id === id);
          if (!crop) return;
          const newName = prompt('Edit crop name:', crop.name) || crop.name;
          const newQty = Number(prompt('Edit quantity (kg):', crop.quantity) || crop.quantity);
          const newPrice = Number(prompt('Edit price per kg (₹):', crop.price) || crop.price);
          if (!newName || newQty <= 0 || newPrice <= 0) {
            alert('Invalid values. Edit cancelled.');
            return;
          }
          crop.name = newName.trim();
          crop.quantity = newQty;
          crop.price = newPrice;
          await utils.fetchAPI(`/crops/${id}`, 'PUT', {
            name: crop.name,
            quantity: crop.quantity,
            price: crop.price
          });
          render.crops();
        }
      } catch (e) {
        console.error('Error handling crop actions:', e);
      }
    },
    updateOrderStatus: async (ev) => {
      if (ev.target.classList.contains('order-status-select')) {
        try {
          const id = ev.target.dataset.id;
          const order = state.orders.find(o => String(o.id) === String(id));
          if (order) {
            order.status = ev.target.value;
            await utils.fetchAPI(`/orders/${id}`, 'PUT', { status: order.status });
            render.orders();
          }
        } catch (e) {
          console.error('Error updating order status:', e);
        }
      }
    },
    deleteOrder: async (ev) => {
      const btn = ev.target.closest('[data-delete-order]');
      if (btn) {
        try {
          const id = btn.dataset.deleteOrder;
          if (confirm('Delete this order?')) {
            await utils.fetchAPI(`/orders/${id}`, 'DELETE');
            state.orders = state.orders.filter(o => String(o.id) !== String(id));
            render.orders();
          }
        } catch (e) {
          console.error('Error deleting order:', e);
        }
      }
    },
    search: utils.debounce(() => {
      DOM.clearSearch.classList.toggle('hidden', !DOM.globalSearch.value.trim());
      render.crops();
      render.orders();
    }, 300),
    clearSearch: () => {
      DOM.globalSearch.value = '';
      DOM.clearSearch.classList.add('hidden');
      render.crops();
      render.orders();
    },
    addSampleOrder: async () => {
      try {
        if (!state.crops.length) {
          alert('Add at least one crop before creating sample orders.');
          return;
        }
        const sample = {
          buyer: 'Local Buyer ' + Math.floor(Math.random() * 90 + 10),
          product: state.crops[Math.floor(Math.random() * state.crops.length)].name,
          qty: Math.floor(Math.random() * 200) + 10,
          status: 'Received'
        };
        const order = await utils.fetchAPI('/orders', 'POST', sample);
        state.orders.unshift(order);
        render.orders();
      } catch (e) {
        console.error('Error adding sample order:', e);
      }
    },
    clearStorage: async () => {
      if (confirm('Clear all data? This will delete all crops and orders from the server.')) {
        try {
          state.crops = [];
          state.orders = [];
          // Note: This is a simple implementation; in production, you'd want a dedicated endpoint to clear all data
          await Promise.all([
            ...state.crops.map(c => utils.fetchAPI(`/crops/${c.id}`, 'DELETE')),
            ...state.orders.map(o => utils.fetchAPI(`/orders/${o.id}`, 'DELETE'))
          ]);
          render.crops();
          render.orders();
        } catch (e) {
          console.error('Error clearing data:', e);
        }
      }
    },
    importSampleData: async () => {
      if (!confirm('Load sample data? This will append sample items to your current data.')) return;
      try {
        await utils.fetchAPI('/sample-data', 'POST');
        state.crops = await utils.fetchAPI('/crops');
        state.orders = await utils.fetchAPI('/orders');
        render.crops();
        render.orders();
      } catch (e) {
        console.error('Error importing sample data:', e);
      }
    }
  };

  // Event bindings
  const bindEvents = () => {
    DOM.cropName.addEventListener('input', handlers.validateForm);
    DOM.cropQty.addEventListener('input', handlers.validateForm);
    DOM.cropPrice.addEventListener('input', handlers.validateForm);
    DOM.form.addEventListener('submit', handlers.addCrop);
    DOM.btnReset.addEventListener('click', handlers.resetForm);
    DOM.cropTbody.addEventListener('change', handlers.updateCropStatus);
    DOM.cropTbody.addEventListener('click', handlers.handleCropActions);
    DOM.ordersTbody.addEventListener('change', handlers.updateOrderStatus);
    DOM.ordersTbody.addEventListener('click', handlers.deleteOrder);
    DOM.globalSearch.addEventListener('input', handlers.search);
    DOM.clearSearch.addEventListener('click', handlers.clearSearch);
    DOM.statusFilter.addEventListener('change', render.crops);
    DOM.sortBy.addEventListener('change', render.crops);
    DOM.btnAddSampleOrder.addEventListener('click', handlers.addSampleOrder);
    DOM.btnClearStorage.addEventListener('click', handlers.clearStorage);
    DOM.btnImportSample.addEventListener('click', handlers.importSampleData);
  };

  // Initialize
  const init = async () => {
    try {
      state.crops = await utils.fetchAPI('/crops');
      state.orders = await utils.fetchAPI('/orders');
      render.crops();
      render.orders();
      handlers.validateForm();
      lucide.createIcons();
      bindEvents();
    } catch (e) {
      console.error('Initialization error:', e);
      DOM.formError.textContent = 'Error initializing app. Please refresh the page.';
      DOM.formError.classList.remove('hidden');
    }
  };

  init();
})();