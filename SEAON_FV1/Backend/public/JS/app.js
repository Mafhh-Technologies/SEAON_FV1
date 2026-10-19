/*
  SEAON ERP FRONTEND CONTROLLER

  This is intentionally one readable file.
  Each section is a small screen:
    dashboard -> inventory -> orders -> production -> BOM -> warehouse
    -> returns -> FIFO -> reports -> alerts.

  It uses the API functions in api.js and never talks to SQLite directly.
*/
document.addEventListener("DOMContentLoaded",()=>{
  if(!Auth.isAuthenticated()){location.href="/app/login.html";return;}

  const state={page:"dashboard",products:[],orders:[],inventory:[],production:[],bom:[],returns:[],batches:[],warehouse:[]};
  const role=Auth.user()?.role||"viewer";
  const $=s=>document.querySelector(s);
  const pageEl=$("#page");

  const pageInfo={
    dashboard:["Dashboard","A simple view of today's operations."],
    inventory:["Inventory","Current stock, minimum levels and stock movements."],
    orders:["Orders","Create and track manufactured and readymade orders."],
    production:["Production","Production queue, output and completion."],
    bom:["BOM / Materials","Map raw and semi-finished materials to products."],
    warehouse:["Warehouse","Inward, putaway, pick, pack and dispatch movements."],
    returns:["Returns","Track returned products from request to redelivery."],
    fifo:["FIFO Batches","Use the oldest stock batch first."],
    reports:["Reports","Simple management, stock and workflow summaries."],
    notifications:["Alerts","Low stock, dead stock and near-expiry alerts."]
  };

  $("#userName").textContent=Auth.user()?.full_name||Auth.user()?.email||"User";
  API.branding.get().then(applyBranding).catch(()=>{});
  API.notifications.list().then(rows=>{const btn=document.querySelector('[data-page="notifications"]');if(!btn)return;const count=rows.filter(n=>!n.is_read).length;let badge=btn.querySelector(".notification-count");if(!badge){badge=document.createElement("span");badge.className="notification-count";btn.appendChild(badge)}badge.textContent=count?String(count):"";badge.style.display=count?"inline-flex":"none";}).catch(()=>{});
  function applyBranding(b){
    const mark=document.querySelector(".brand-mark"); if(mark){mark.textContent=b.logo_text||"S";mark.style.background=b.logo_color||"#2563eb";mark.style.borderRadius=b.logo_style==="circle"?"50%":b.logo_style==="square"?"4px":"12px";}
    const title=document.querySelector(".brand strong"); if(title)title.textContent=b.company_name||"SEAON ERP";
    const tagline=document.querySelector(".brand small"); if(tagline)tagline.textContent=b.tagline||"Manufacturing & Stock";
  }
  $("#roleBadge").textContent=role.replaceAll("-"," ").replace(/\b\w/g,c=>c.toUpperCase());
  if(!["super-admin","admin"].includes(role)) $("#adminLink").classList.add("hidden");
  const perms=Auth.user()?.permissions||[];
  const can=(code)=>perms.includes("*")||perms.includes(code);
  const menuPermission={
    inventory:"inventory.view",orders:"orders.view",production:"production.view",
    bom:"bom.read",warehouse:"warehouse.receive",returns:"returns.view",fifo:"inventory.fifo",reports:"reports.view"
  };
  document.querySelectorAll(".nav-item[data-page]").forEach(btn=>{
    const need=menuPermission[btn.dataset.page];
    if(need && !can(need)) btn.classList.add("hidden");
  });

  $("#mobileMenu").onclick=()=>$("#sidebar").classList.toggle("open");
  $("#logoutBtn").onclick=()=>Auth.logout();
  $("#refreshBtn").onclick=()=>loadPage(state.page);

  document.querySelectorAll(".nav-item[data-page]").forEach(btn=>{
    btn.onclick=()=>{state.page=btn.dataset.page; document.querySelectorAll(".nav-item[data-page]").forEach(x=>x.classList.remove("active"));btn.classList.add("active");$("#sidebar").classList.remove("open");loadPage(state.page);}
  });

  function esc(v){return String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));}
  function num(v){return Number(v||0).toLocaleString("en-IN",{maximumFractionDigits:2});}
  function date(v){return v?new Date(v).toLocaleDateString("en-IN"):"-";}
  function money(v){return `₹${num(v)}`;}
  function badge(status){
    const s=String(status||"").toLowerCase();
    const type=["completed","closed","delivered"].includes(s)?"success":["cancelled","dead"].includes(s)?"danger":["pending","requested","inspection","in-progress","repair","replacement"].includes(s)?"warning":"neutral";
    return `<span class="badge ${type}">${esc(String(status||"").replaceAll("-"," "))}</span>`;
  }
  function empty(message="No records found."){return `<div class="empty">${esc(message)}</div>`;}
  function toast(message,type="success"){const x=document.createElement("div");x.className=`toast ${type}`;x.textContent=message;$("#toastArea").appendChild(x);setTimeout(()=>x.remove(),3500);}
  function setHead(page){$("#pageTitle").textContent=pageInfo[page][0];$("#pageSubtitle").textContent=pageInfo[page][1];}
  function modal(title,body){
    document.querySelector(".modal-backdrop")?.remove();
    const wrap=document.createElement("div");wrap.className="modal-backdrop show";wrap.innerHTML=`<div class="modal"><div class="modal-head"><h2>${title}</h2><button class="close" data-close>×</button></div>${body}</div>`;
    document.body.appendChild(wrap);wrap.onclick=e=>{if(e.target===wrap||e.target.closest("[data-close]"))wrap.remove()};return wrap;
  }

  // Fetch the server-owned data needed by a screen, then render that screen.
  // Keeping reads here prevents stale cross-screen state after mutations.
  async function loadPage(page){
    setHead(page);
    pageEl.innerHTML=`<div class="card"><div class="empty">Loading ${esc(pageInfo[page][0])}...</div></div>`;
    try{
      if(page==="dashboard")return renderDashboard(await API.dashboard());
      if(page==="inventory"){state.inventory=await API.inventory.list();state.products=await API.products.list();return renderInventory();}
      if(page==="orders"){state.orders=await API.orders.list();state.products=await API.products.list();return renderOrders();}
      if(page==="production"){state.production=await API.production.list();state.products=await API.products.list();return renderProduction();}
      if(page==="bom"){state.bom=await API.bom.list();state.products=await API.products.list();return renderBOM();}
      if(page==="warehouse"){state.warehouse=await API.warehouse.list();state.products=await API.products.list();return renderWarehouse();}
      if(page==="returns"){state.returns=await API.returns.list();state.orders=await API.orders.list();return renderReturns();}
      if(page==="fifo"){state.batches=await API.inventory.batches();state.products=await API.products.list();return renderFIFO();}
      if(page==="reports")return renderReports(await API.reports());
      if(page==="notifications")return renderNotifications();
    }catch(e){pageEl.innerHTML=`<div class="card"><div class="error-box">${esc(e.message)}</div></div>`;toast(e.message,"error");}
  }

  function renderDashboard(d){
    pageEl.innerHTML=`
      <div class="grid grid-4">
        ${kpi("Orders",d.orders_total,"Total orders")}
        ${kpi("Pending",d.orders_pending,"Need attention","warning")}
        ${kpi("Production",d.production_active,"Active jobs")}
        ${kpi("Low Stock",d.low_stock,"Items at/below minimum",d.low_stock?"danger":"success")}
      </div>
      <div class="grid grid-3" style="margin-top:16px">
        ${kpi("Inventory Items",d.inventory_items,"Tracked products")}
        ${kpi("Returns",d.returns_open,"Open return cases")}
        ${kpi("FIFO Batches",d.fifo_batches,"Batches with stock")}
      </div>
      <div class="grid grid-2" style="margin-top:16px">
        <div class="card"><div class="section-head"><h2>Recent Orders</h2><button class="btn small" data-go="orders">Open Orders</button></div>${orderTable(d.recent_orders||[])}</div>
        <div class="card"><div class="section-head"><h2>Stock Health</h2><button class="btn small" data-go="inventory">Open Inventory</button></div>
          <div class="chart-bars">
            ${bar("Low stock",d.stock_health?.low_stock||0,Math.max(1,d.inventory_items))}
            ${bar("Dead stock",d.stock_health?.dead_stock||0,Math.max(1,d.inventory_items))}
            ${bar("Near expiry",d.stock_health?.near_expiry||0,Math.max(1,d.fifo_batches))}
          </div>
        </div>
      </div>`;
    pageEl.querySelectorAll("[data-go]").forEach(x=>x.onclick=()=>{state.page=x.dataset.go;document.querySelector(`[data-page="${state.page}"]`).click()});
  }
  function kpi(label,value,hint,type="neutral"){return `<div class="kpi"><div class="label">${label}</div><strong class="${type==="danger"?"danger-text":""}">${num(value)}</strong><div class="hint">${hint}</div></div>`}
  function bar(label,value,max){const pct=Math.min(100,Math.round((Number(value)/max)*100));return `<div class="bar-row"><span>${label}</span><div class="bar"><span style="width:${pct}%"></span></div><strong>${num(value)}</strong></div>`}

  function renderInventory(){
    pageEl.innerHTML=`
      <div class="section-head"><div><h2>Inventory Management</h2><p class="muted">Create, edit, receive, adjust and remove products while keeping live stock connected to orders.</p></div><div class="actions"><button class="btn primary" data-action="add-product">+ Add Product</button><button class="btn" data-action="receive">Receive Stock</button></div></div>
      <div class="filters"><input id="invSearch" placeholder="Search item, SKU or location"><select id="invFilter"><option value="">All stock</option><option value="low">Low stock</option></select></div>
      <div class="card"><div class="table-wrap"><table class="data-table"><thead><tr><th>Product</th><th>SKU</th><th>Qty</th><th>Unit</th><th>Minimum</th><th>Location</th><th>Status</th><th>Actions</th></tr></thead><tbody id="inventoryRows"></tbody></table></div></div>`;
    const draw=()=>{
      const q=( $("#invSearch")?.value||"").toLowerCase(), low=$("#invFilter")?.value==="low";
      const rows=state.inventory.filter(i=>(!q||`${i.product_name} ${i.sku} ${i.location}`.toLowerCase().includes(q))&&(!low||Number(i.quantity)<=Number(i.minimum_stock)));
      $("#inventoryRows").innerHTML=rows.length?rows.map(i=>`<tr><td><strong>${esc(i.product_name)}</strong></td><td>${esc(i.sku)}</td><td>${num(i.quantity)}</td><td>${esc(i.unit)}</td><td>${num(i.minimum_stock)}</td><td>${esc(i.location)}</td><td>${badge(Number(i.quantity)<=Number(i.minimum_stock)?"Low Stock":"Healthy")}</td><td><div class="actions"><button class="btn small" data-adjust="${i.product}">Adjust</button><button class="btn small" data-edit-product="${i.product}">Edit</button><button class="btn small danger" data-delete-product="${i.product}">Delete</button></div></td></tr>`).join(""):`<tr><td colspan="8">${empty()}</td></tr>`;
      $("#inventoryRows").querySelectorAll("[data-adjust]").forEach(b=>b.onclick=()=>adjustStock(b.dataset.adjust));
      $("#inventoryRows").querySelectorAll("[data-edit-product]").forEach(b=>b.onclick=()=>editProduct(b.dataset.editProduct));
      $("#inventoryRows").querySelectorAll("[data-delete-product]").forEach(b=>b.onclick=()=>deleteProduct(b.dataset.deleteProduct));
    };
    $("#invSearch").oninput=draw;$("#invFilter").onchange=draw;draw();
    pageEl.querySelector('[data-action="add-product"]').onclick=addProduct;
    pageEl.querySelector('[data-action="receive"]').onclick=receiveStock;
  }
  async function adjustStock(id){
    const q=prompt("Stock change. Use + to add and - to remove:","0");if(q===null)return;
    try{await API.inventory.adjust(id,Number(q),"Manual adjustment");toast("Stock updated.");loadPage("inventory")}catch(e){toast(e.message,"error")}
  }
  function productFormMarkup(p={}){return `<form id="productForm" class="form-grid">
    ${field("Name","name","text","Product name",true)}${field("SKU","sku","text","Unique SKU",true)}
    ${select("Product Type","product_type",["raw-material","component","finished"])}${select("Unit","unit",["pcs","kg","g","m","cm","roll","boxes"])}
    ${field("Minimum stock","minimum_stock","number","0")}${field("Location","location","text","Main Store")}
    <div class="field full"><button class="btn primary" type="submit">Save Product</button></div></form>`}
  function addProduct(){
    const m=modal("Add Product",productFormMarkup());
    m.querySelector('[name="minimum_stock"]').value="0";
    m.querySelector("#productForm").onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));d.minimum_stock=Number(d.minimum_stock||0);try{await API.products.create({...d,quantity:0});m.remove();toast("Product created.");loadPage("inventory")}catch(ex){toast(ex.message,"error")}};
  }
  function editProduct(id){
    const item=state.products.find(p=>String(p.id)===String(id));if(!item)return;
    const m=modal("Edit Product",productFormMarkup(item));const f=m.querySelector("#productForm");
    for(const key of ["name","sku","product_type","unit","minimum_stock","location"])if(f.elements[key])f.elements[key].value=item[key]??"";
    f.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(f));d.minimum_stock=Number(d.minimum_stock||0);try{await API.products.update(id,d);m.remove();toast("Product updated.");loadPage("inventory")}catch(ex){toast(ex.message,"error")}};
  }
  async function deleteProduct(id){if(!confirm("Delete this product? Products linked to orders or BOM records cannot be deleted."))return;try{await API.products.remove(id);toast("Product deleted.");loadPage("inventory")}catch(e){toast(e.message,"error")}}
  function receiveStock(){
    const options=state.products.map(p=>`<option value="${p.id}">${esc(p.name)} (${esc(p.sku)})</option>`).join("");
    const m=modal("Receive Stock",`<form id="receiveForm" class="form-grid"><div class="field full"><label>Product</label><select name="product">${options}</select></div>${field("Quantity","quantity","number","0",true)}${field("Vendor","vendor","text","Supplier name")}${field("Batch code","batch_code","text","Optional")}${field("Unit cost","unit_cost","number","0")}${field("Received date","received_date","date","")}${field("Expiry date","expiry_date","date","")}${field("Reference","reference","text","Purchase / GRN number")}<div class="field full"><button class="btn primary" type="submit">Receive Stock</button></div></form>`);
    m.querySelector("#receiveForm").onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));data.product=Number(data.product);data.quantity=Number(data.quantity);try{await API.inventory.receive(data);m.remove();toast("Stock received.");loadPage("inventory")}catch(ex){toast(ex.message,"error")}};
  }

  function renderOrders(){
    const statuses=[["","All Orders"],["new-order","New Order"],["in-production","In Production"],["packed","Packed"],["dispatched","Dispatched"]];
    pageEl.innerHTML=`<div class="section-head"><div><h2>Order Management</h2><p class="muted">Orders are checked against finished stock or BOM material availability before saving.</p></div><button class="btn primary" data-action="add">+ Create Order</button></div>
      <div class="filters"><input id="orderSearch" placeholder="Search order, customer or product"><select id="orderStatus">${statuses.map(x=>`<option value="${x[0]}">${x[1]}</option>`).join("")}</select></div>
      <div class="card"><div class="table-wrap"><table class="data-table"><thead><tr><th>Order</th><th>Customer</th><th>Type</th><th>Product</th><th>Qty</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody id="orderRows"></tbody></table></div></div>`;
    const draw=()=>{const q=$("#orderSearch").value.toLowerCase(),status=$("#orderStatus").value;const rows=state.orders.filter(o=>(!status||o.status===status)&&(!q||`${o.order_number} ${o.customer_name} ${o.product_name}`.toLowerCase().includes(q)));
      $("#orderRows").innerHTML=rows.length?rows.map(o=>{const next=o.status==="new-order"?"packed":o.status==="packed"?"dispatched":"";return `<tr><td><strong>${esc(o.order_number)}</strong></td><td>${esc(o.customer_name)}</td><td>${esc(o.order_type||"manufactured")}</td><td>${esc(o.product_name)}</td><td>${num(o.quantity)} ${esc(o.unit||"")}</td><td>${badge(o.status)}</td><td>${date(o.created_at)}</td><td>${next?`<button class="btn small" data-transition="${o.id}" data-next-status="${next}">${next==="packed"?"Mark Packed":"Dispatch"}</button>`:"—"}</td></tr>`}).join(""):`<tr><td colspan="8">${empty()}</td></tr>`;
      $("#orderRows").querySelectorAll("[data-transition]").forEach(b=>b.onclick=async()=>{try{await API.orders.transition(b.dataset.transition,b.dataset.nextStatus);toast(`Order marked ${b.dataset.nextStatus.replaceAll("-"," ")}.`);loadPage("orders")}catch(e){toast(e.message,"error")}});
    };
    $("#orderSearch").oninput=draw;$("#orderStatus").onchange=draw;draw();
    pageEl.querySelector('[data-action="add"]').onclick=addOrder;
  }
  function addOrder(){
    const options=state.products.filter(p=>p.is_active!==false).map(p=>`<option value="${p.id}">${esc(p.name)} (${esc(p.sku)})</option>`).join("");
    const m=modal("Create Order",`<form id="orderForm" class="form-grid">
      ${field("Customer","customer_name","text","Customer name",true)}${field("Customer email","customer_email","email","")}
      ${field("Your sender / reply-to email","sender_email","email","you@company.com",true)}
      <div class="field full"><label for="vendor_emails">Vendor email addresses <span class="muted">(multiple allowed)</span></label><textarea id="vendor_emails" name="vendor_emails" rows="3" required placeholder="vendor1@example.com, vendor2@example.com\nYou can separate addresses with commas, semicolons, or new lines."></textarea><small class="muted">SEAON sends the order details to every address when you click Create Order. Replies go to your sender email above.</small></div>
      ${field("Vendor WhatsApp","vendor_whatsapp","tel","+919876543210")}
      ${select("Order type","order_type",["manufactured","readymade"])}<div class="field"><label>Product</label><select name="product" required>${options}</select></div>
      ${field("Quantity","quantity","number","1",true)}<div class="field full"><label>Notes</label><textarea name="notes"></textarea></div>
      <div class="field full"><div id="availabilityPanel" class="alert warning">Select a product and quantity to check live stock and BOM materials.</div></div>
      <div class="field full"><button class="btn primary" id="createOrderButton" type="submit" disabled>Create Order</button></div></form>`);
    const form=m.querySelector("#orderForm"), qty=form.elements.quantity, product=form.elements.product, type=form.elements.order_type, panel=m.querySelector("#availabilityPanel"), submit=m.querySelector("#createOrderButton");
    let availabilityTimer;
    async function checkAvailability(){
      submit.disabled=true;const q=Number(qty.value);if(!product.value||!q||q<=0){panel.className="alert warning";panel.textContent="Select a product and enter a quantity to check availability.";return;}
      panel.className="alert warning";panel.textContent="Checking live inventory and BOM materials…";
      try{const a=await API.orders.availability(product.value,q,type.value);const lines=(a.materials||[]).map(x=>`<div><strong>${esc(x.name)}</strong>: required ${num(x.required)} ${esc(x.unit)} · available ${num(x.available)} ${esc(x.unit)} — ${x.sufficient?"Sufficient":"INSUFFICIENT"}</div>`).join("");
        panel.className=a.available?"alert success":"alert danger";panel.innerHTML=`<strong>${esc(a.message)}</strong>${type.value==="readymade"?`<div>Finished stock: ${num(a.finished_stock)} ${esc(a.unit)} · Requested: ${num(a.required)} ${esc(a.unit)}</div>`:`<div>Finished goods will be added when production completes.</div>`}${lines}`;submit.disabled=!a.available;
      }catch(e){panel.className="alert danger";panel.textContent=e.message;submit.disabled=true;}
    }
    [qty,product,type].forEach(el=>el.addEventListener("input",()=>{clearTimeout(availabilityTimer);availabilityTimer=setTimeout(checkAvailability,200)}));
    checkAvailability();
    form.onsubmit=async e=>{e.preventDefault();submit.disabled=true;const d=Object.fromEntries(new FormData(form));d.product=Number(d.product);d.quantity=Number(d.quantity);
      // Accept multiple recipient emails separated by commas, semicolons, or new lines.
      d.vendor_emails=String(d.vendor_emails||"").split(/[\s,;]+/).map(v=>v.trim()).filter(Boolean);
      d.vendor_email=d.vendor_emails[0]||""; // Backward-compatible primary recipient.
      try{const result=await API.orders.create(d);m.remove();const n=result.notifications||{};const email=(n.email||{}).status||"not_requested";const recipientCount=(n.email||{}).recipient_count||d.vendor_emails.length;toast(`Order created. Vendor email: ${email} (${recipientCount} recipient(s)).`);if(result.production_created){state.page="production";document.querySelector('[data-page="production"]').click()}else loadPage("orders")}catch(ex){toast(ex.message,"error");submit.disabled=false;checkAvailability()}};
  }

  function renderProduction(){
    pageEl.innerHTML=`<div class="section-head"><div><h2>Production Queue</h2><p class="muted">Work orders, output and completion.</p></div><button class="btn primary" data-action="add">+ Start Production</button></div>
      <div class="card"><div class="table-wrap"><table class="data-table"><thead><tr><th>Job</th><th>Product</th><th>Customer</th><th>Qty</th><th>Produced</th><th>Operator</th><th>Status</th><th>Action</th></tr></thead><tbody>${state.production.length?state.production.map(p=>`<tr><td>${esc(p.production_number)}</td><td>${esc(p.product_name)}</td><td>${esc(p.customer_name||"-")}</td><td>${num(p.quantity)}</td><td>${num(p.produced_quantity)}</td><td>${esc(p.assigned_to||"-")}</td><td>${badge(p.status)}</td><td>${p.status!=="completed"?`<button class="btn small" data-complete="${p.id}">Complete</button>`:"—"}</td></tr>`).join(""):`<tr><td colspan="8">${empty()}</td></tr>`}</tbody></table></div></div>`;
    pageEl.querySelector('[data-action="add"]').onclick=addProduction;
    pageEl.querySelectorAll("[data-complete]").forEach(b=>b.onclick=async()=>{try{await API.production.complete(b.dataset.complete);toast("Production completed.");loadPage("production")}catch(e){toast(e.message,"error")}});
  }
  function addProduction(){
    const options=state.products.filter(p=>p.product_type==="finished").map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join("");
    const m=modal("Start Production",`<form id="productionForm" class="form-grid">
      <div class="field"><label>Finished product</label><select name="product">${options}</select></div>
      ${field("Customer","customer_name","text","Optional")}${field("Quantity","quantity","number","1",true)}${field("Assigned operator","assigned_to","text","Operator name")}
      <div class="field full"><button class="btn primary" type="submit">Start Production</button></div></form>`);
    m.querySelector("#productionForm").onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));d.product=Number(d.product);d.quantity=Number(d.quantity);try{await API.production.create(d);m.remove();toast("Production job started.");loadPage("production")}catch(ex){toast(ex.message,"error")}};
  }

  function renderBOM(){
    const options=state.products.filter(p=>p.product_type!=="raw-material").map(p=>`<option value="${p.id}">${esc(p.name)} (${esc(p.sku)})</option>`).join("");
    pageEl.innerHTML=`<div class="section-head"><div><h2>Bill of Materials</h2><p class="muted">Choose a finished or semi-finished product to view and manage only its materials.</p></div></div>
      <div class="card"><div class="card-body"><div class="field" style="max-width:520px"><label>Product</label><select id="bomProduct"><option value="">Select a product to view/edit BOM</option>${options}</select></div></div></div>
      <div id="bomContent" class="card" style="margin-top:16px">${empty("Select a product above to view or edit its bill of materials.")}</div>
      <div class="alert info" style="margin-top:16px">BOM quantities are used for live material checks during order creation. Material stock is consumed atomically when a manufactured order is accepted.</div>`;
    const selectProduct=$("#bomProduct");selectProduct.onchange=draw;
    function draw(){const id=selectProduct.value;if(!id){$("#bomContent").innerHTML=empty("Select a product above to view or edit its bill of materials.");return;}const rows=state.bom.filter(x=>String(x.product)===String(id));
      $("#bomContent").innerHTML=`<div class="section-head"><div><h2>Material Requirements — ${esc(state.products.find(p=>String(p.id)===String(id))?.name||"")}</h2><p class="muted">Set the quantity of each component needed for one finished unit.</p></div><button class="btn primary" data-add-bom>+ Add Material</button></div><div class="table-wrap"><table class="data-table"><thead><tr><th>#</th><th>Raw Material</th><th>Quantity per Unit</th><th>Unit</th><th>Actions</th></tr></thead><tbody>${rows.length?rows.map((x,i)=>`<tr><td>${i+1}</td><td>${esc(x.component_name)}</td><td>${num(x.quantity_per_unit)}</td><td>${esc(x.unit)}</td><td><div class="actions"><button class="btn small" data-edit-bom="${x.id}">Edit</button><button class="btn small danger" data-delete-bom="${x.id}">Delete</button></div></td></tr>`).join(""):`<tr><td colspan="5">${empty("No BOM materials defined for this product yet.")}</td></tr>`}</tbody></table></div>`;
      $("#bomContent [data-add-bom]").onclick=()=>addBOM(id);
      $("#bomContent [data-delete-bom]").forEach(b=>b.onclick=async()=>{if(!confirm("Delete this BOM item?"))return;try{await API.bom.remove(b.dataset.deleteBom);state.bom=await API.bom.list();draw();toast("BOM item deleted.")}catch(e){toast(e.message,"error")}});
      $("#bomContent [data-edit-bom]").forEach(b=>b.onclick=()=>editBOM(b.dataset.editBom));
    }
    async function addBOM(productId){
      const components=state.products.filter(p=>String(p.id)!==String(productId)&&p.product_type!=="finished");
      const componentOptions=components.map(p=>`<option value="${p.id}">${esc(p.name)} (${esc(p.sku)})</option>`).join("");
      const m=modal("Add BOM Material",`<form id="bomForm" class="form-grid"><div class="field full"><label>Raw material / component</label><select name="component_product" required>${componentOptions}</select></div>${field("Quantity per Unit","quantity_per_unit","number","1",true)}${select("Unit","unit",["pcs","kg","g","m","roll","boxes"])}<div class="field full"><button class="btn primary" type="submit">Save Material</button></div></form>`);
      m.querySelector("#bomForm").onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));d.product=Number(productId);d.component_product=Number(d.component_product);d.quantity_per_unit=Number(d.quantity_per_unit);try{await API.bom.create(d);state.bom=await API.bom.list();m.remove();draw();toast("BOM material saved.")}catch(ex){toast(ex.message,"error")}};
    }
    function editBOM(id){const item=state.bom.find(x=>String(x.id)===String(id));if(!item)return;const components=state.products.filter(p=>String(p.id)!==String(item.product)&&p.product_type!=="finished");const opts=components.map(p=>`<option value="${p.id}">${esc(p.name)} (${esc(p.sku)})</option>`).join("");const m=modal("Edit BOM Material",`<form id="bomEditForm" class="form-grid"><div class="field full"><label>Raw material / component</label><select name="component_product" required>${opts}</select></div>${field("Quantity per Unit","quantity_per_unit","number","1",true)}${select("Unit","unit",["pcs","kg","g","m","roll","boxes"])}<div class="field full"><button class="btn primary" type="submit">Save Changes</button></div></form>`);const f=m.querySelector("#bomEditForm");f.elements.component_product.value=item.component_product;f.elements.quantity_per_unit.value=item.quantity_per_unit;f.elements.unit.value=item.unit;f.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(f));d.component_product=Number(d.component_product);d.quantity_per_unit=Number(d.quantity_per_unit);try{await API.bom.update(id,d);state.bom=await API.bom.list();m.remove();draw();toast("BOM material updated.")}catch(ex){toast(ex.message,"error")}}}
  }

  // Show the warehouse movement ledger returned by the backend.
  function renderWarehouse(){
    pageEl.innerHTML=`<div class="section-head"><div><h2>Warehouse</h2><p class="muted">Track inward, putaway, picking, packing and dispatch.</p></div><button class="btn primary" data-action="add">+ Record Movement</button></div>
    <div class="card"><div class="table-wrap"><table class="data-table"><thead><tr><th>Date</th><th>Product</th><th>Movement</th><th>Qty</th><th>Reference</th><th>Notes</th></tr></thead><tbody>${state.warehouse.length?state.warehouse.map(x=>`<tr><td>${date(x.created_at)}</td><td>${esc(x.product_name)}</td><td>${badge(x.transaction_type)}</td><td>${num(x.quantity)}</td><td>${esc(x.reference)}</td><td>${esc(x.notes)}</td></tr>`).join(""):`<tr><td colspan="6">${empty()}</td></tr>`}</tbody></table></div></div>`;
    pageEl.querySelector('[data-action="add"]').onclick=addWarehouse;
  }
  // Collect a warehouse movement and submit it through the authenticated API.
  function addWarehouse(){
    const options=state.products.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join("");
    const m=modal("Warehouse Movement",`<form id="warehouseForm" class="form-grid">
      <div class="field"><label>Product</label><select name="product">${options}</select></div>
      ${select("Movement","transaction_type",["inward","putaway","pick","pack","dispatch","return-receive"])}
      ${field("Quantity","quantity","number","1",true)}${field("Reference","reference","text","Order / GRN / Dispatch number")}
      ${field("Notes","notes","text","Optional")}
      <div class="field full"><button class="btn primary" type="submit">Save Movement</button></div></form>`);
    m.querySelector("#warehouseForm").onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));d.product=Number(d.product);d.quantity=Number(d.quantity);try{await API.warehouse.create(d);m.remove();toast("Warehouse movement saved.");loadPage("warehouse")}catch(ex){toast(ex.message,"error")}};
  }

  // Render return cases and expose the next workflow action for each case.
  function renderReturns(){
    pageEl.innerHTML=`<div class="section-head"><div><h2>Returns</h2><p class="muted">Delivered → return requested → inspection → repair/replacement → redelivery.</p></div><button class="btn primary" data-action="add">+ New Return</button></div>
    <div class="card"><div class="table-wrap"><table class="data-table"><thead><tr><th>Order</th><th>Customer</th><th>Product</th><th>Reason</th><th>Status</th><th>Mode</th><th>Action</th></tr></thead><tbody>${state.returns.length?state.returns.map(x=>`<tr><td>${esc(x.order_number)}</td><td>${esc(x.customer_name)}</td><td>${esc(x.product_name)}</td><td>${esc(x.reason)}</td><td>${badge(x.status)}</td><td>${esc(x.replacement_mode)}</td><td><button class="btn small" data-next="${x.id}">Next step</button></td></tr>`).join(""):`<tr><td colspan="7">${empty()}</td></tr>`}</tbody></table></div></div>`;
    pageEl.querySelector('[data-action="add"]').onclick=addReturn;
    pageEl.querySelectorAll("[data-next]").forEach(b=>b.onclick=()=>nextReturn(b.dataset.next));
  }
  function addReturn(){
    const options=state.orders.map(o=>`<option value="${o.id}">${esc(o.order_number)} — ${esc(o.customer_name)}</option>`).join("");
    const m=modal("Create Return",`<form id="returnForm" class="form-grid">
      <div class="field full"><label>Order</label><select name="order">${options}</select></div>
      ${field("Returned quantity", "return_quantity", "number", "Defaults to full order quantity", true)}
      <div class="field full"><label>Return reason</label><textarea name="reason" required></textarea></div>
      <div class="field full"><label>Damage notes</label><textarea name="damage_notes"></textarea></div>
      ${select("Resolution","replacement_mode",["repair","replacement","refund"])}
      <div class="field full"><button class="btn primary" type="submit">Create Return</button></div></form>`);
    m.querySelector("#returnForm").onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));d.order=Number(d.order);try{if(!d.return_quantity)d.return_quantity=state.orders.find(o=>String(o.id)===String(d.order))?.quantity||1;d.return_quantity=Number(d.return_quantity);await API.returns.create(d);m.remove();toast("Return created.");loadPage("returns")}catch(ex){toast(ex.message,"error")}};
  }
  async function nextReturn(id){
    const steps=["requested","received","inspection","repair","replacement","redelivery","closed"];
    const item=state.returns.find(x=>String(x.id)===String(id));if(!item)return;
    const next=steps[Math.min(steps.indexOf(item.status)+1,steps.length-1)];
    try{await API.returns.update(id,{status:next});toast("Return updated.");loadPage("returns")}catch(e){toast(e.message,"error")}
  }

  // Display stock batches in oldest-received-first order as supplied by Django.
  function renderFIFO(){
    pageEl.innerHTML=`<div class="section-head"><div><h2>FIFO Batches</h2><p class="muted">Oldest stock is consumed before newer stock.</p></div><button class="btn primary" data-action="consume">Consume FIFO</button></div>
    <div class="card"><div class="table-wrap"><table class="data-table"><thead><tr><th>Batch</th><th>Product</th><th>Received</th><th>Vendor</th><th>Original Qty</th><th>Remaining</th><th>Expiry</th></tr></thead><tbody>${state.batches.length?state.batches.map(b=>`<tr><td>${esc(b.batch_code)}</td><td>${esc(b.product_name)}</td><td>${date(b.received_date)}</td><td>${esc(b.vendor||"-")}</td><td>${num(b.quantity)}</td><td>${num(b.remaining_quantity)}</td><td>${date(b.expiry_date)}</td></tr>`).join(""):`<tr><td colspan="7">${empty("No batch records yet. Receive stock to create batches.")}</td></tr>`}</tbody></table></div></div>`;
    pageEl.querySelector('[data-action="consume"]').onclick=consumeFIFO;
  }
  function consumeFIFO(){
    const options=state.products.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join("");
    const m=modal("FIFO Stock Consumption",`<form id="fifoForm" class="form-grid"><div class="field full"><label>Product</label><select name="product">${options}</select></div>${field("Quantity","quantity","number","1",true)}${field("Reference","reference","text","Production / Pick number")}<div class="field full"><button class="btn primary">Consume Oldest Stock</button></div></form>`);
    m.querySelector("#fifoForm").onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));d.product=Number(d.product);d.quantity=Number(d.quantity);try{const r=await API.inventory.consume(d);toast(`FIFO consumed: ${r.allocations.map(x=>x.batch+" ("+x.quantity+")").join(", ")}`);m.remove();loadPage("fifo")}catch(ex){toast(ex.message,"error")}};
  }

  // Reports use the normalized stock/order/production/return counts from API.
  async function renderReports(data){
    pageEl.innerHTML=`<div class="grid grid-3">${kpi("Low Stock",data.stock.low_stock,"At/below minimum",data.stock.low_stock?"danger":"success")}${kpi("Dead Stock",data.stock.dead_stock,"No movement in 90 days")}${kpi("Near Expiry",data.stock.near_expiry,"Within 30 days","warning")}</div>
      <div class="grid grid-3" style="margin-top:16px">
      ${simpleReport("Orders",data.orders_by_status)}${simpleReport("Production",data.production_by_status)}${simpleReport("Returns",data.returns_by_status)}</div>`;
  }
  function simpleReport(title,obj){return `<div class="card"><h2>${title}</h2><div class="chart-bars">${Object.entries(obj).map(([k,v])=>bar(k,v,Math.max(1,...Object.values(obj)))).join("")}</div></div>`}

  async function renderNotifications(){
    const rows=await API.notifications.list();
    pageEl.innerHTML=`<div class="section-head"><div><h2>Notifications</h2><p class="muted">Order workflow, stock checks and system activity.</p></div><div class="actions"><button class="btn" data-read-all>Mark All as Read</button><button class="btn danger" data-clear-all>Clear All</button></div></div><div class="card"><div class="table-wrap"><table class="data-table"><thead><tr><th>Type</th><th>Notification</th><th>Details</th><th>Time</th><th>Status</th><th>Action</th></tr></thead><tbody>${rows.length?rows.map(n=>`<tr><td>${badge(n.kind)}</td><td><strong>${esc(n.title)}</strong></td><td>${esc(n.message)}</td><td>${new Date(n.created_at).toLocaleString("en-IN")}</td><td>${badge(n.is_read?"read":"unread")}</td><td>${n.is_read?"—":`<button class="btn small" data-read="${n.id}">Mark Read</button>`}</td></tr>`).join(""):`<tr><td colspan="6">${empty("No notifications yet.")}</td></tr>`}</tbody></table></div></div>`;
    pageEl.querySelector("[data-read-all]").onclick=async()=>{await API.notifications.action("read_all");renderNotifications()};
    pageEl.querySelector("[data-clear-all]").onclick=async()=>{if(!confirm("Clear all notifications?"))return;await API.notifications.action("clear_all");renderNotifications()};
    pageEl.querySelectorAll("[data-read]").forEach(b=>b.onclick=async()=>{await API.notifications.action("read",b.dataset.read);renderNotifications()});
  }

  function field(label,name,type="text",placeholder="",required=false){return `<div class="field"><label>${label}</label><input name="${name}" type="${type}" placeholder="${placeholder}" ${required?"required":""}></div>`}
  function select(label,name,values){return `<div class="field"><label>${label}</label><select name="${name}">${values.map(v=>`<option value="${v}">${v.replaceAll("-"," ")}</option>`).join("")}</select></div>`}
  function orderTable(rows){return rows.length?`<div class="table-wrap"><table class="data-table"><thead><tr><th>Order</th><th>Customer</th><th>Product</th><th>Qty</th><th>Status</th></tr></thead><tbody>${rows.map(o=>`<tr><td>${esc(o.order_number)}</td><td>${esc(o.customer_name)}</td><td>${esc(o.product__name)}</td><td>${num(o.quantity)}</td><td>${badge(o.status)}</td></tr>`).join("")}</tbody></table></div>`:empty()}

  // First screen.
  loadPage("dashboard");
});
