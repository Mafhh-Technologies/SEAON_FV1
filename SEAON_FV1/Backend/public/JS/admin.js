document.addEventListener("DOMContentLoaded",()=>{
  if(!Auth.isAuthenticated()){location.href="/app/login.html";return;}
  const me=Auth.user();
  if(!["super-admin","admin"].includes(me?.role)){location.href="/app/index.html";return;}
  const page=document.querySelector("#adminPage");
  const toast=(m,type="success")=>{const x=document.createElement("div");x.className=`toast ${type}`;x.textContent=m;document.querySelector("#adminToast").appendChild(x);setTimeout(()=>x.remove(),3500)};
  const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
  const state={roles:[],permissions:[],users:[]};

  document.querySelector("#adminUser").textContent=me.full_name||me.email;
  // Apply saved branding on the admin page too, not only the main ERP screen.
  API.branding.get().then(applyAdminBranding).catch(()=>{});
  function applyAdminBranding(b){
    const mark=document.querySelector(".brand-mark");
    if(mark){mark.textContent=b.logo_text||"S";mark.style.background=b.logo_color||"#2563eb";mark.style.borderRadius=b.logo_style==="circle"?"50%":b.logo_style==="square"?"4px":"12px";}
    const title=document.querySelector(".brand strong");if(title)title.textContent=b.company_name||"SEAON ERP";
    const tagline=document.querySelector(".brand small");if(tagline)tagline.textContent=b.tagline||"Manufacturing & Stock";
  }
  document.querySelectorAll("#adminNav [data-section]").forEach(b=>b.onclick=()=>{document.querySelectorAll("#adminNav .nav-item").forEach(x=>x.classList.remove("active"));b.classList.add("active");load(b.dataset.section)});

  async function load(section){
    page.innerHTML=`<div class="card"><div class="empty">Loading...</div></div>`;
    try{
      if(section==="overview")return overview();
      if(section==="users"){state.users=await adminAPI.users();state.roles=await adminAPI.roles();return users();}
      if(section==="roles"){state.roles=await adminAPI.roles();state.permissions=await adminAPI.permissions();return roles();}
      if(section==="branding")return branding(await adminAPI.branding());
      if(section==="stock")return stock(await adminAPI.stock());
      if(section==="audit")return audit(await adminAPI.audit());
    }catch(e){page.innerHTML=`<div class="card"><div class="error-box">${esc(e.message)}</div></div>`}
  }

  async function overview(){
    const d=await adminAPI.summary();
    page.innerHTML=`<div class="grid grid-4">${k("Users",d.users)}${k("Active Users",d.active_users)}${k("Roles",d.roles)}${k("Audit Events",d.audit_events)}</div>
      <div class="grid grid-2" style="margin-top:16px"><div class="card"><h2>Simple admin workflow</h2><p class="muted">1. Create users → 2. Assign a role → 3. Adjust permissions → 4. Review audit logs.</p></div>
      <div class="card"><h2>Imported stock</h2><strong style="font-size:30px">${d.stock_rows}</strong><p class="muted">Rows imported from the supplied Excel sheets.</p></div></div>`;
  }
  function k(label,v){return `<div class="kpi"><div class="label">${label}</div><strong>${Number(v||0).toLocaleString("en-IN")}</strong></div>`}


  async function branding(b){
    page.innerHTML=`<div class="section-head"><div><h2>Logo & Company Branding</h2><p class="muted">Use the fixed SEAON logo component and customize its initials, color and shape.</p></div></div>
      <div class="card"><form id="brandingForm" class="form-grid">
        ${f("Company name","company_name","text","SEAON",true)}${f("Tagline","tagline","text","Manufacturing & Stock")}
        ${f("Logo text (up to 5 characters)","logo_text","text","S",true)}
        <div class="field"><label>Logo background color</label><input name="logo_color" type="color" value="${esc(b.logo_color||"#2563eb")}" required></div>
        <div class="field"><label>Logo shape</label><select name="logo_style"><option value="rounded">Rounded square</option><option value="circle">Circle</option><option value="square">Square</option></select></div>
        <div class="field full"><div style="display:flex;align-items:center;gap:12px"><div id="logoPreview" class="brand-mark" style="background:${esc(b.logo_color||"#2563eb")};border-radius:${b.logo_style==="circle"?"50%":b.logo_style==="square"?"4px":"12px"}">${esc(b.logo_text||"S")}</div><div><strong id="brandPreviewName">${esc(b.company_name||"SEAON")}</strong><div id="brandPreviewTagline" class="muted">${esc(b.tagline||"")}</div></div></div></div>
        <div class="field full"><button class="btn primary" type="submit">Save Branding</button></div>
      </form></div>`;
    const form=page.querySelector("#brandingForm");form.elements.company_name.value=b.company_name||"SEAON";form.elements.tagline.value=b.tagline||"Manufacturing & Stock";form.elements.logo_text.value=b.logo_text||"S";form.elements.logo_style.value=b.logo_style||"rounded";
    const updatePreview=()=>{const text=form.elements.logo_text.value.trim().slice(0,5)||"S",color=form.elements.logo_color.value,shape=form.elements.logo_style.value;const mark=page.querySelector("#logoPreview");mark.textContent=text;mark.style.background=color;mark.style.borderRadius=shape==="circle"?"50%":shape==="square"?"4px":"12px";page.querySelector("#brandPreviewName").textContent=form.elements.company_name.value||"SEAON";page.querySelector("#brandPreviewTagline").textContent=form.elements.tagline.value||""};
    form.addEventListener("input",updatePreview);form.addEventListener("change",updatePreview);
    form.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(form));d.logo_text=d.logo_text.trim().slice(0,5)||"S";try{await adminAPI.saveBranding(d);toast("Branding saved. The logo and company identity are now updated.");applyAdminBranding(await adminAPI.branding());load("branding")}catch(ex){toast(ex.message,"error")}};
  }

  function users(){
    page.innerHTML=`<div class="section-head"><div><h2>Users</h2><p class="muted">Create and control application accounts.</p></div></div>
    <div class="card"><form id="userForm" class="form-grid">
      ${f("Full name","full_name","text","e.g. Rahul Sharma",true)}${f("Email","email","email","name@company.com",true)}
      ${f("Temporary password","password","password","Minimum 8 characters",true)}
      <div class="field"><label>Role</label><select name="role">${state.roles.map(r=>`<option value="${r.name}">${esc(r.name)}</option>`).join("")}</select></div>
      <div class="field full"><button class="btn primary">Create User</button></div>
    </form></div>
    <div class="card" style="margin-top:16px"><div class="table-wrap"><table class="data-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Action</th></tr></thead><tbody>${state.users.map(u=>`<tr><td>${esc(u.full_name||"-")}</td><td>${esc(u.email)}</td><td>${esc(u.role)}</td><td>${u.is_active?'<span class="badge success">Active</span>':'<span class="badge danger">Inactive</span>'}</td><td>${u.email===me.email?"—":`<button class="btn small" data-user="${u.id}" data-active="${u.is_active}">${u.is_active?"Deactivate":"Activate"}</button>`}</td></tr>`).join("")}</tbody></table></div></div>`;
    page.querySelector("#userForm").onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));try{await adminAPI.createUser(d);toast("User created.");load("users")}catch(x){toast(x.message,"error")}};
    page.querySelectorAll("[data-user]").forEach(b=>b.onclick=async()=>{try{await adminAPI.updateUser(b.dataset.user,{is_active:b.dataset.active!=="true"});toast("User status updated.");load("users")}catch(e){toast(e.message,"error")}});
  }

  function roles(){
    page.innerHTML=`<div class="section-head"><div><h2>Roles & Permissions</h2><p class="muted">A role is simply a saved set of allowed actions.</p></div></div>
    <div class="card"><form id="roleForm" class="form-grid">${f("Role name","name","text","e.g. Quality Manager",true)}${f("Description","description","text","What this role does")}
      <div class="field full"><label>Permissions</label><div class="permission-grid">${state.permissions.map(p=>`<label><input type="checkbox" name="permission" value="${p.code}"> ${esc(p.label)}</label>`).join("")}</div></div>
      <div class="field full"><button class="btn primary">Create Role</button></div></form></div>
    <div class="grid grid-2" style="margin-top:16px">${state.roles.map(r=>`<div class="card"><h3>${esc(r.name)} ${r.is_system?'<span class="badge neutral">System</span>':''}</h3><p class="muted">${esc(r.description)}</p><p><strong>${(r.permissions||[]).length}</strong> permissions</p></div>`).join("")}</div>`;
    page.querySelector("#roleForm").onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));d.permissions=[...e.target.querySelectorAll('input[name="permission"]:checked')].map(x=>x.value);try{await adminAPI.createRole(d);toast("Role created.");load("roles")}catch(x){toast(x.message,"error")}};
  }

  function stock(rows){
    page.innerHTML=`<div class="section-head"><div><h2>Imported Stock</h2><p class="muted">This is the raw spreadsheet data kept for traceability.</p></div><button class="btn primary" id="reimport">Re-import Excel</button></div>
    <div class="filters"><input id="stockSearch" placeholder="Search item"></div>
    <div class="card"><div class="table-wrap"><table class="data-table"><thead><tr><th>Category</th><th>Item</th><th>Size</th><th>Colour</th><th>Available</th><th>Minimum</th><th>Source</th></tr></thead><tbody id="stockRows"></tbody></table></div></div>`;
    const draw=()=>{const q=(document.querySelector("#stockSearch").value||"").toLowerCase();const r=rows.filter(x=>`${x.item_name} ${x.category} ${x.source_file}`.toLowerCase().includes(q));document.querySelector("#stockRows").innerHTML=r.map(x=>`<tr><td>${esc(x.category)}</td><td>${esc(x.item_name)}</td><td>${esc(x.size)}</td><td>${esc(x.color)}</td><td>${x.available_stock??"-"} ${esc(x.unit)}</td><td>${x.minimum_stock??"-"}</td><td>${esc(x.source_file)} / ${esc(x.source_sheet)} / row ${x.source_row||"-"}</td></tr>`).join("")||`<tr><td colspan="7">${empty()}</td></tr>`};
    document.querySelector("#stockSearch").oninput=draw;draw();
    document.querySelector("#reimport").onclick=async()=>{try{await adminAPI.reimport();toast("Excel data imported.");load("stock")}catch(e){toast(e.message,"error")}};
  }

  function audit(rows){
    page.innerHTML=`<div class="section-head"><div><h2>Audit Log</h2><p class="muted">Who changed what and when.</p></div></div><div class="card"><div class="table-wrap"><table class="data-table"><thead><tr><th>Date</th><th>User</th><th>Module</th><th>Action</th><th>Description</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${new Date(x.created_at).toLocaleString("en-IN")}</td><td>${esc(x.user)}</td><td>${esc(x.module)}</td><td>${esc(x.action)}</td><td>${esc(x.description)}</td></tr>`).join("")||`<tr><td colspan="5">${empty()}</td></tr>`}</tbody></table></div></div>`;
  }

  const f=(label,name,type,placeholder,required=false)=>`<div class="field"><label>${label}</label><input name="${name}" type="${type}" placeholder="${placeholder}" ${required?"required":""}></div>`;
  const empty=()=>`<div class="empty">No records.</div>`;
  const adminAPI={
    summary:()=>API.request("/admin/summary/"),users:()=>API.request("/admin/users/"),
    createUser:d=>API.request("/admin/users/",{method:"POST",body:JSON.stringify(d)}),
    updateUser:(id,d)=>API.request(`/admin/users/${id}/`,{method:"PATCH",body:JSON.stringify(d)}),
    roles:()=>API.request("/admin/roles/"),permissions:()=>API.request("/admin/permissions/"),
    createRole:d=>API.request("/admin/roles/",{method:"POST",body:JSON.stringify(d)}),
    stock:()=>API.request("/admin/stock/"),audit:()=>API.request("/admin/audit/"),
    reimport:()=>API.request("/admin/reimport/",{method:"POST"}),
    branding:()=>API.branding.get(),
    saveBranding:d=>API.branding.save(d)
  };
  document.querySelector("#adminLogout").onclick=()=>Auth.logout();
  load("overview");
});
