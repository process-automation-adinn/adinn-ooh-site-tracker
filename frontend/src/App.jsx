import { useEffect, useMemo, useState } from 'react';
import { apiFetch, clearSession, getApiBase, getStoredUser, getToken, setSession } from './api.js';

const emptyForm = {
  hoarding_location: '',
  landlord_location: '',
  landlord_name: '',
  landlord_phone: '',
  landlord_email: '',
  secondary_contact_name: '',
  secondary_contact_phone: '',
  height_ft: '',
  width_ft: '',
  rental_type: 'Monthly',
  rent_amount: '',
  advance_amount: '',
  light_type: 'Front Light',
  side_type: 'Single',
  towards_1: '',
  towards_2: '',
  latitude: '',
  longitude: '',
  agreement_tenure: '3 Years',
  agreement_start_date: '',
  agreement_end_date: '',
};

const emptyFiles = {
  site_photo_file: null,
  landlord_photo_file: null,
  aadhaar_file: null,
  pan_file: null,
  property_tax_file: null,
  passbook_file: null,
};

const sectionRemarkLabels = [
  ['site_location', 'Site Location'],
  ['landlord_contact', 'Landlord Contact Details'],
  ['size_rental_display', 'Size, Rental & Display'],
  ['documents', 'Photos & Documents'],
  ['gps_agreement', 'GPS & Agreement'],
];

function siteToRemarks(site) {
  return site?.remarks || {};
}


function defaultSizeBoxes(sideType = 'Single') {
  return sideType === 'Double'
    ? [
        { label: 'Side 1', width_ft: '', height_ft: '' },
        { label: 'Side 2', width_ft: '', height_ft: '' },
      ]
    : [{ label: 'Side 1', width_ft: '', height_ft: '' }];
}

function normalizeSizeBoxesForForm(site) {
  if (Array.isArray(site?.size_boxes) && site.size_boxes.length) {
    if (site?.side_type === 'Double') {
      const first = site.size_boxes[0] || {};
      const second = site.size_boxes[1] || {};
      return [
        { label: 'Side 1', width_ft: first.width_ft ?? '', height_ft: first.height_ft ?? '' },
        { label: 'Side 2', width_ft: second.width_ft ?? '', height_ft: second.height_ft ?? '' },
      ];
    }
    const first = site.size_boxes[0] || {};
    return [{ label: 'Side 1', width_ft: first.width_ft ?? '', height_ft: first.height_ft ?? '' }];
  }
  return [{ label: 'Side 1', width_ft: site?.width_ft ?? '', height_ft: site?.height_ft ?? '' }];
}

function calculateSizeArea(sizeBoxes) {
  return sizeBoxes.reduce((sum, box) => {
    const width = Number(box.width_ft || 0);
    const height = Number(box.height_ft || 0);
    return sum + (width > 0 && height > 0 ? width * height : 0);
  }, 0);
}

function formatDateTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
}

function siteToForm(site) {
  return {
    hoarding_location: site?.hoarding_location || '',
    landlord_location: site?.landlord_location || '',
    landlord_name: site?.landlord_name || '',
    landlord_phone: site?.landlord_phone || '',
    landlord_email: site?.landlord_email || '',
    secondary_contact_name: site?.secondary_contact_name || '',
    secondary_contact_phone: site?.secondary_contact_phone || '',
    height_ft: site?.height_ft ?? '',
    width_ft: site?.width_ft ?? '',
    rental_type: site?.rental_type || 'Monthly',
    rent_amount: site?.rent_amount ?? '',
    advance_amount: site?.advance_amount ?? '',
    light_type: site?.light_type || 'Front Light',
    side_type: site?.side_type || 'Single',
    towards_1: site?.towards_1 || '',
    towards_2: site?.towards_2 || '',
    latitude: site?.latitude ?? '',
    longitude: site?.longitude ?? '',
    agreement_tenure: site?.agreement_tenure || '3 Years',
    agreement_start_date: site?.agreement_start_date || '',
    agreement_end_date: site?.agreement_end_date || '',
  };
}

function formatCurrency(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(number);
}

function addYearsMinusOneDay(startDate, years) {
  if (!startDate) return '';
  const d = new Date(`${startDate}T00:00:00`);
  d.setFullYear(d.getFullYear() + years);
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      setSession(data.access_token, data.user);
      onLogin(data.user);
    } catch (err) {
      setError(err.message || 'Unable to sign in. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell deployment-login">
      <section className="login-hero">
        <div className="brand-row logo-brand-row">
          <img src="/adinn-logo.png" alt="ADINN Advertising Services Ltd." className="brand-logo login-brand-logo" />
        </div>
        <div className="hero-copy">
          <p className="eyebrow">OOH Site Tracker</p>
          <h1>Secure access for field teams and administrators.</h1>
          <p className="muted">
            Capture hoarding locations, landlord details, photos, documents, GPS data,
            agreement dates and section remarks in one deployment-ready dashboard.
          </p>
        </div>
        <div className="login-highlights">
          <span>Role-based access</span>
          <span>Admin-controlled CRUD permissions</span>
          <span>Neon PostgreSQL data storage</span>
          <span>Responsive field visit form</span>
        </div>
      </section>

      <section className="login-card login-card-deployed">
        <div className="login-card-header">
          <p className="eyebrow">Authorized Sign In</p>
          <h2>Welcome back</h2>
          <p className="muted">Use the work email and password provided by your ADINN administrator.</p>
        </div>

        <form onSubmit={submit} className="login-form">
          <label htmlFor="email">Work Email</label>
          <input
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            autoComplete="email"
            placeholder="name@company.com"
            required
          />

          <label htmlFor="password">Password</label>
          <div className="password-field">
            <input
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="Enter your password"
              required
            />
            <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>

          {error && <div className="alert error">{error}</div>}
          <button className="primary-btn login-submit" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in securely'}
          </button>
        </form>

        <div className="security-note">
          <strong>Production-ready login</strong>
          <span>No demo credentials are shown on this page. User accounts and CRUD permissions are managed by the admin.</span>
        </div>
      </section>
    </main>
  );
}

function Header({ user, activeTab, setActiveTab, onLogout }) {
  return (
    <header className="app-header">
      <div className="header-brand">
        <img src="/adinn-logo.png" alt="ADINN Advertising Services Ltd." className="header-logo" />
        <div>
          <p className="eyebrow">ADINN Internal App</p>
          <h1>OOH Site Tracker</h1>
        </div>
      </div>
      <div className="header-actions">
        <div className="user-pill">
          <span>{user?.name}</span>
          <small>{user?.role}{user?.role !== 'admin' && user?.can_crud ? ' · CRUD allowed' : ''}</small>
        </div>
        <button className="ghost-btn" onClick={onLogout}>Logout</button>
      </div>
      <nav className="tabs">
        <button className={activeTab === 'dashboard' ? 'active' : ''} onClick={() => setActiveTab('dashboard')}>Dashboard</button>
        <button className={activeTab === 'add' ? 'active' : ''} onClick={() => setActiveTab('add')}>Add OOH Site</button>
        <button className={activeTab === 'records' ? 'active' : ''} onClick={() => setActiveTab('records')}>Records</button>
        {user?.role === 'admin' && <button className={activeTab === 'users' ? 'active' : ''} onClick={() => setActiveTab('users')}>Employees</button>}
      </nav>
    </header>
  );
}

function Dashboard({ sites }) {
  const uploadedDocs = sites.reduce((sum, site) => {
    const docs = site.documents || {};
    return sum + ['site_photo_uploaded', 'landlord_photo_uploaded', 'aadhaar_uploaded', 'pan_uploaded', 'property_tax_uploaded', 'passbook_uploaded'].filter((key) => docs[key]).length;
  }, 0);
  const monthly = sites.filter((site) => site.rental_type === 'Monthly').length;
  const expiringSoon = sites.filter((site) => {
    const end = new Date(site.agreement_end_date);
    const today = new Date();
    const diff = (end - today) / (1000 * 60 * 60 * 24);
    return diff >= 0 && diff <= 90;
  }).length;

  return (
    <section className="page-stack">
      <div className="grid stats-grid">
        <Stat title="Total OOH Sites" value={sites.length} hint="All submitted records" />
        <Stat title="Monthly Rentals" value={monthly} hint="Sites on monthly rental" />
        <Stat title="Agreements Expiring" value={expiringSoon} hint="Next 90 days" />
      </div>
      <div className="panel two-column-panel">
        <div>
          <h2>Field Visit Workflow</h2>
          <p className="muted">Open the app on mobile, add the hoarding and landlord details, upload site photos/documents, fetch GPS and submit. Admin can review and export all records.</p>
        </div>
        <div className="mini-metrics">
          <span>{uploadedDocs} document files marked uploaded</span>
          <span>{sites.filter((s) => s.latitude && s.longitude).length} sites with GPS</span>
          <span>{sites.filter((s) => s.light_type === 'LED').length} LED sites</span>
        </div>
      </div>
    </section>
  );
}

function Stat({ title, value, hint }) {
  return (
    <div className="stat-card">
      <span>{title}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}

function Field({ label, children, required }) {
  return (
    <label className="field">
      <span>{label}{required && <b>*</b>}</span>
      {children}
    </label>
  );
}

function SectionHeader({ number, title, description, remarkKey, remarks, onRemarkChange }) {
  return (
    <div className="section-title section-title-with-remark">
      <div className="section-heading">
        <span>{number}</span>
        <div><h2>{title}</h2><p>{description}</p></div>
      </div>
      <label className="section-remark">
        <span>{title} Remark</span>
        <textarea
          rows="2"
          value={remarks[remarkKey] || ''}
          onChange={(e) => onRemarkChange(remarkKey, e.target.value)}
          placeholder={`Add remark for ${title}`}
        />
      </label>
    </div>
  );
}

function UploadField({ label, name, file, onChange }) {
  return (
    <div className="upload-card">
      <div>
        <strong>{label}</strong>
        <small>{file ? file.name : 'jpg, jpeg, png or pdf'}</small>
      </div>
      <div className="upload-actions">
        <label className="file-btn">
          Upload
          <input type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => onChange(name, e.target.files[0] || null)} />
        </label>
        <label className="checkbox-line">
          <input type="checkbox" checked={Boolean(file)} readOnly /> Uploaded
        </label>
      </div>
    </div>
  );
}

function SiteForm({ onCreated, initialSite = null, mode = 'create', onSaved, onCancel }) {
  const isEdit = mode === 'edit';
  const [form, setForm] = useState(() => (initialSite ? siteToForm(initialSite) : emptyForm));
  const [sizeBoxes, setSizeBoxes] = useState(() => (initialSite ? normalizeSizeBoxesForForm(initialSite) : defaultSizeBoxes(emptyForm.side_type)));
  const [files, setFiles] = useState(emptyFiles);
  const [remarks, setRemarks] = useState(() => (initialSite ? siteToRemarks(initialSite) : {}));
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);

  useEffect(() => {
    setForm(initialSite ? siteToForm(initialSite) : emptyForm);
    setSizeBoxes(initialSite ? normalizeSizeBoxesForForm(initialSite) : defaultSizeBoxes(emptyForm.side_type));
    setFiles(emptyFiles);
    setRemarks(initialSite ? siteToRemarks(initialSite) : {});
    setMessage('');
    setError('');
  }, [initialSite?.id]);

  const area = useMemo(() => {
    const total = calculateSizeArea(sizeBoxes);
    return total > 0 ? total.toFixed(2) : '';
  }, [sizeBoxes]);

  function update(name, value) {
    setForm((prev) => {
      const next = { ...prev, [name]: value };
      if (name === 'side_type' && value === 'Single') next.towards_2 = '';
      if (name === 'side_type') {
        setSizeBoxes((previous) => {
          if (value === 'Single') return [{ ...(previous[0] || {}), label: 'Side 1', width_ft: previous[0]?.width_ft || '', height_ft: previous[0]?.height_ft || '' }];
          const first = previous[0] || { width_ft: '', height_ft: '' };
          const second = previous[1] || { width_ft: '', height_ft: '' };
          return [
            { ...first, label: 'Side 1' },
            { ...second, label: 'Side 2' },
          ];
        });
      }
      if (name === 'agreement_start_date' || name === 'agreement_tenure') {
        const years = next.agreement_tenure === '5 Years' ? 5 : 3;
        next.agreement_end_date = addYearsMinusOneDay(next.agreement_start_date, years);
      }
      return next;
    });
  }

  function updateSizeBox(index, field, value) {
    setSizeBoxes((previous) => previous.map((box, idx) => (idx === index ? { ...box, [field]: value } : box)));
  }

  function updateFile(name, file) {
    setFiles((prev) => ({ ...prev, [name]: file }));
  }

  function updateRemark(name, value) {
    setRemarks((prev) => ({ ...prev, [name]: value }));
  }

  function fetchGps() {
    setError('');
    if (!navigator.geolocation) {
      setError('GPS is not supported in this browser.');
      return;
    }
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        update('latitude', position.coords.latitude.toFixed(7));
        update('longitude', position.coords.longitude.toFixed(7));
        setGpsLoading(false);
      },
      (err) => {
        setError(err.message || 'GPS permission denied.');
        setGpsLoading(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  }

  async function saveSite(createAgreement = false) {
    setError('');
    setMessage('');
    const validBoxes = sizeBoxes.filter((box) => Number(box.width_ft) > 0 && Number(box.height_ft) > 0);
    if (!validBoxes.length) {
      setError('At least one valid size box is required.');
      return;
    }
    setLoading(true);
    try {
      const firstBox = validBoxes[0];
      const normalizedBoxes = validBoxes.map((box, index) => ({
        label: box.label || `Size ${index + 1}`,
        width_ft: Number(box.width_ft),
        height_ft: Number(box.height_ft),
        area_sqft: Number(box.width_ft) * Number(box.height_ft),
      }));
      const body = new FormData();
      Object.entries(form).forEach(([key, value]) => body.append(key, value ?? ''));
      body.set('width_ft', firstBox.width_ft ?? '');
      body.set('height_ft', firstBox.height_ft ?? '');
      body.append('size_boxes_json', JSON.stringify(normalizedBoxes));
      body.append('remarks_json', JSON.stringify(remarks));
      if (!isEdit) body.append('create_agreement', createAgreement ? 'true' : 'false');
      Object.entries(files).forEach(([key, file]) => {
        if (file) body.append(key, file);
      });
      const saved = await apiFetch(isEdit ? `/api/sites/${initialSite.id}` : '/api/sites', { method: isEdit ? 'PUT' : 'POST', body });
      setMessage(isEdit ? `OOH site #${saved.id} updated successfully.` : `OOH site #${saved.id} saved successfully.`);
      if (!isEdit) {
        setForm(emptyForm);
        setSizeBoxes(defaultSizeBoxes(emptyForm.side_type));
        setFiles(emptyFiles);
        setRemarks({});
        onCreated?.();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        onSaved?.();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function submit(e) {
    e.preventDefault();
    await saveSite(false);
  }

  async function confirmAndCreateAgreement() {
    const ok = window.confirm('Create agreement for this OOH site? Warning: once confirmed, employees cannot edit or delete this record. Only admin can edit/delete after agreement is created.');
    if (!ok) return;
    await saveSite(true);
  }

  return (
    <form className="site-form page-stack" onSubmit={submit}>
      {message && <div className="alert success">{message}</div>}
      {error && <div className="alert error">{error}</div>}

      <section className="form-section">
        <SectionHeader number="01" title="Site Location" description="Enter the hoarding and landlord address manually." remarkKey="site_location" remarks={remarks} onRemarkChange={updateRemark} />
        <div className="grid two">
          <Field label="Location of Hoarding" required>
            <textarea value={form.hoarding_location} onChange={(e) => update('hoarding_location', e.target.value)} required rows="4" placeholder="Enter full site address" />
          </Field>
          <Field label="Location of Landlord" required>
            <textarea value={form.landlord_location} onChange={(e) => update('landlord_location', e.target.value)} required rows="4" placeholder="Enter landlord address" />
          </Field>
        </div>
      </section>

      <section className="form-section">
        <SectionHeader number="02" title="Landlord Contact Details" description="Primary and secondary contact details." remarkKey="landlord_contact" remarks={remarks} onRemarkChange={updateRemark} />
        <div className="grid three">
          <Field label="Landlord Name" required><input value={form.landlord_name} onChange={(e) => update('landlord_name', e.target.value)} required /></Field>
          <Field label="Phone Number" required><input value={form.landlord_phone} onChange={(e) => update('landlord_phone', e.target.value)} inputMode="numeric" pattern="[0-9]{10}" required placeholder="10 digit number" /></Field>
          <Field label="Email"><input type="email" value={form.landlord_email} onChange={(e) => update('landlord_email', e.target.value)} /></Field>
          <Field label="Secondary Contact Name"><input value={form.secondary_contact_name} onChange={(e) => update('secondary_contact_name', e.target.value)} /></Field>
          <Field label="Secondary Phone"><input value={form.secondary_contact_phone} onChange={(e) => update('secondary_contact_phone', e.target.value)} inputMode="numeric" pattern="[0-9]{10}" /></Field>
        </div>
      </section>

      <section className="form-section">
        <SectionHeader number="03" title="Size, Rental & Display" description="Enter side-wise size, rental and display details." remarkKey="size_rental_display" remarks={remarks} onRemarkChange={updateRemark} />
        <div className="grid three">
          <Field label="Side" required>
            <select value={form.side_type} onChange={(e) => update('side_type', e.target.value)}>
              <option>Single</option><option>Double</option>
            </select>
          </Field>
          <Field label="Light" required>
            <select value={form.light_type} onChange={(e) => update('light_type', e.target.value)}>
              <option>Front Light</option><option>Non Light</option><option>LED</option>
            </select>
          </Field>
        </div>
        <div className="size-box-panel">
          <div className="size-box-head">
            <strong>{form.side_type === 'Double' ? 'Two-sided size details' : 'Size details'}</strong>
          </div>
          {sizeBoxes.map((box, index) => {
            const towardsKey = index === 0 ? 'towards_1' : 'towards_2';
            const showTowards = form.side_type === 'Single' ? index === 0 : index < 2;
            return (
              <div className="size-box-row" key={index}>
                <Field label="Label"><input value={box.label || `Side ${index + 1}`} onChange={(e) => updateSizeBox(index, 'label', e.target.value)} placeholder={`Side ${index + 1}`} /></Field>
                <Field label="Width in feet" required><input type="number" min="0" step="0.01" value={box.width_ft} onChange={(e) => updateSizeBox(index, 'width_ft', e.target.value)} required /></Field>
                <Field label="Height in feet" required><input type="number" min="0" step="0.01" value={box.height_ft} onChange={(e) => updateSizeBox(index, 'height_ft', e.target.value)} required /></Field>
                <Field label="Area"><input value={Number(box.width_ft || 0) > 0 && Number(box.height_ft || 0) > 0 ? (Number(box.width_ft) * Number(box.height_ft)).toFixed(2) : ''} readOnly placeholder="Auto" /></Field>
                {showTowards && (
                  <Field label={form.side_type === 'Single' ? 'Towards' : `Towards ${index + 1}`} required>
                    <input
                      value={form[towardsKey]}
                      onChange={(e) => update(towardsKey, e.target.value)}
                      required
                      placeholder={index === 0 ? 'Example: Chennai to Tambaram' : 'Example: Tambaram to Chennai'}
                    />
                  </Field>
                )}
              </div>
            );
          })}
        </div>
        <div className="grid four">
          <Field label="Rental" required>
            <select value={form.rental_type} onChange={(e) => update('rental_type', e.target.value)}>
              <option>Annually</option><option>Half Yearly</option><option>Quarterly</option><option>Monthly</option>
            </select>
          </Field>
          <Field label="Rent in Rs"><input type="number" min="0" step="1" value={form.rent_amount} onChange={(e) => update('rent_amount', e.target.value)} /></Field>
          <Field label="Advance in Rs"><input type="number" min="0" step="1" value={form.advance_amount} onChange={(e) => update('advance_amount', e.target.value)} /></Field>
        </div>

      </section>

      <section className="form-section">
        <SectionHeader number="04" title="Photos & Documents" description={isEdit ? 'Upload a new file only if you want to replace the existing one.' : 'Upload site photo, landlord photo, Aadhaar, PAN, property tax and passbook files.'} remarkKey="documents" remarks={remarks} onRemarkChange={updateRemark} />
        <div className="grid two uploads-grid">
          <UploadField label="Site Photo" name="site_photo_file" file={files.site_photo_file} onChange={updateFile} />
          <UploadField label="Landlord Photo" name="landlord_photo_file" file={files.landlord_photo_file} onChange={updateFile} />
          <UploadField label="Aadhaar Card Photo" name="aadhaar_file" file={files.aadhaar_file} onChange={updateFile} />
          <UploadField label="PAN Card Photo" name="pan_file" file={files.pan_file} onChange={updateFile} />
          <UploadField label="Property Tax Photo" name="property_tax_file" file={files.property_tax_file} onChange={updateFile} />
          <UploadField label="Passbook Photo" name="passbook_file" file={files.passbook_file} onChange={updateFile} />
        </div>
        {isEdit && initialSite?.documents && (
          <div className="current-docs-box">
            <strong>Current uploaded documents</strong>
            <div className="docs-list">
              <DocLink label="Site Photo" uploaded={initialSite.documents.site_photo_uploaded} url={initialSite.documents.site_photo_file_url} />
              <DocLink label="Landlord Photo" uploaded={initialSite.documents.landlord_photo_uploaded} url={initialSite.documents.landlord_photo_file_url} />
              <DocLink label="Aadhaar" uploaded={initialSite.documents.aadhaar_uploaded} url={initialSite.documents.aadhaar_file_url} />
              <DocLink label="PAN" uploaded={initialSite.documents.pan_uploaded} url={initialSite.documents.pan_file_url} />
              <DocLink label="Property Tax" uploaded={initialSite.documents.property_tax_uploaded} url={initialSite.documents.property_tax_file_url} />
              <DocLink label="Passbook" uploaded={initialSite.documents.passbook_uploaded} url={initialSite.documents.passbook_file_url} />
            </div>
          </div>
        )}
      </section>

      <section className="form-section">
        <SectionHeader number="05" title="GPS & Agreement" description="Fetch latitude and longitude from the field visit device." remarkKey="gps_agreement" remarks={remarks} onRemarkChange={updateRemark} />
        <div className="gps-card">
          <button className="secondary-btn" type="button" onClick={fetchGps} disabled={gpsLoading}>{gpsLoading ? 'Fetching GPS...' : 'Fetch GPS'}</button>
          <Field label="Latitude"><input value={form.latitude} onChange={(e) => update('latitude', e.target.value)} placeholder="Auto fetched" /></Field>
          <Field label="Longitude"><input value={form.longitude} onChange={(e) => update('longitude', e.target.value)} placeholder="Auto fetched" /></Field>
        </div>
        <div className="grid three">
          <Field label="Agreement Tenure" required>
            <select value={form.agreement_tenure} onChange={(e) => update('agreement_tenure', e.target.value)}>
              <option>3 Years</option><option>5 Years</option>
            </select>
          </Field>
          <Field label="Agreement Start Date" required><input type="date" value={form.agreement_start_date} onChange={(e) => update('agreement_start_date', e.target.value)} required /></Field>
          <Field label="Agreement End Date" required><input type="date" value={form.agreement_end_date} onChange={(e) => update('agreement_end_date', e.target.value)} required /></Field>
        </div>
      </section>

      <div className="sticky-submit">
        <div>
          <strong>{isEdit ? 'Ready to update?' : 'Ready to submit?'}</strong>
          <span>Rent: {formatCurrency(form.rent_amount)} | Advance: {formatCurrency(form.advance_amount)}</span>
        </div>
        <div className="submit-actions">
          {isEdit && <button className="ghost-btn" type="button" onClick={onCancel}>Cancel</button>}
          {!isEdit && <button className="secondary-btn" type="button" onClick={confirmAndCreateAgreement} disabled={loading}>{loading ? 'Saving...' : 'Create Agreement'}</button>}
          <button className="primary-btn" type="submit" disabled={loading}>{loading ? (isEdit ? 'Updating...' : 'Saving...') : (isEdit ? 'Update OOH Site' : 'Submit OOH Site')}</button>
        </div>
      </div>
    </form>
  );
}

function Records({ sites, reload, user }) {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const isAdmin = user?.role === 'admin';
  const hasEmployeeCrud = Boolean(user?.can_crud);
  const canCrudFor = (site) => isAdmin || (hasEmployeeCrud && site.created_by_user_id === user?.id && !site.agreement_created);
  const canCreateAgreement = (site) => !site.agreement_created && (isAdmin || site.created_by_user_id === user?.id);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return sites.filter((site) => [
      site.hoarding_location,
      site.landlord_location,
      site.landlord_name,
      site.landlord_phone,
      site.rental_type,
      site.light_type,
      site.side_type,
    ].join(' ').toLowerCase().includes(q));
  }, [sites, query]);

  async function exportExcel() {
    setExporting(true);
    try {
      const response = await apiFetch('/api/sites/export/excel');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'adinn_ooh_sites.xlsx';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    } finally {
      setExporting(false);
    }
  }

  async function downloadSiteExport(site, format) {
    try {
      const response = await apiFetch(`/api/sites/${site.id}/export/${format}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ooh_site_${site.id}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    }
  }

  async function createAgreement(site) {
    if (!canCreateAgreement(site)) return;
    const ok = window.confirm('Create agreement for this OOH site? Warning: once confirmed, employees cannot edit or delete this record. Only admin can edit/delete after agreement is created.');
    if (!ok) return;
    try {
      await apiFetch(`/api/sites/${site.id}/agreement`, { method: 'POST' });
      await reload();
      if (selected?.id === site.id) setSelected(null);
    } catch (err) {
      alert(err.message);
    }
  }

  async function deleteRecord(site) {
    if (!canCrudFor(site)) return;
    const ok = window.confirm(`Delete OOH site #${site.id} for ${site.landlord_name}? This cannot be undone.`);
    if (!ok) return;
    setDeletingId(site.id);
    try {
      await apiFetch(`/api/sites/${site.id}`, { method: 'DELETE' });
      await reload();
      if (selected?.id === site.id) setSelected(null);
      if (editing?.id === site.id) setEditing(null);
    } catch (err) {
      alert(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  async function afterEditSaved() {
    setEditing(null);
    await reload();
  }

  return (
    <section className="page-stack">
      <div className="toolbar">
        <input className="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by site, landlord, rental, light..." />
        <button className="secondary-btn" onClick={reload}>Refresh</button>
        {isAdmin && <button className="primary-btn" onClick={exportExcel} disabled={exporting}>{exporting ? 'Exporting...' : 'Export Excel'}</button>}
      </div>

      {!isAdmin && !hasEmployeeCrud && <div className="alert info">Employees can add/view their own records. CRUD is enabled by default unless Admin blocks it or Agreement is created.</div>}
      {!isAdmin && hasEmployeeCrud && <div className="alert info">You can edit/delete your own records until Agreement is created. Once Agreement is created, only Admin can edit/delete.</div>}

      <div className="records-grid">
        {filtered.map((site) => (
          <article key={site.id} className="record-card">
            <div className="record-head">
              <span>#{site.id}</span>
              <strong>{site.landlord_name}</strong>
            </div>
            <p>{site.hoarding_location}</p>
            <div className="tags">
              <em>{site.area_sqft} sqft</em>
              <em>{site.rental_type}</em>
              <em>{site.light_type}</em>
              <em>{site.side_type}</em>
              <em className={site.agreement_created ? 'agreement-tag created' : 'agreement-tag pending'}>{site.agreement_status || (site.agreement_created ? 'Agreement Created' : 'Agreement Not Created')}</em>
            </div>
            <div className="record-footer">
              <small>Uploaded: {formatDateTime(site.created_at)} · End: {site.agreement_end_date}</small>
              <div className="record-actions">
                <button className="ghost-btn" onClick={() => setSelected(site)}>View</button>
                <button className="ghost-btn" onClick={() => downloadSiteExport(site, 'pdf')}>PDF</button>
                <button className="ghost-btn" onClick={() => downloadSiteExport(site, 'docx')}>DOCX</button>
                {canCreateAgreement(site) && <button className="secondary-btn" onClick={() => createAgreement(site)}>Agreement</button>}
                {canCrudFor(site) && <button className="secondary-btn" onClick={() => setEditing(site)}>Edit</button>}
                {canCrudFor(site) && <button className="danger-btn" onClick={() => deleteRecord(site)} disabled={deletingId === site.id}>{deletingId === site.id ? 'Deleting...' : 'Delete'}</button>}
              </div>
            </div>
          </article>
        ))}
      </div>

      {filtered.length === 0 && <div className="empty-state">No records found.</div>}
      {selected && <SiteModal site={selected} onClose={() => setSelected(null)} />}
      {editing && <EditSiteModal site={editing} onClose={() => setEditing(null)} onSaved={afterEditSaved} />}
    </section>
  );
}

function DocLink({ label, uploaded, url }) {
  const fullUrl = url ? `${getApiBase()}${url}` : '';
  return (
    <div className="doc-row">
      <span>{label}</span>
      {uploaded && url ? <a href={fullUrl} target="_blank" rel="noreferrer">Open file</a> : <em>Not uploaded</em>}
    </div>
  );
}

function EditSiteModal({ site, onClose, onSaved }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal wide-modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>×</button>
        <p className="eyebrow">Admin CRUD</p>
        <h2>Edit OOH Site #{site.id}</h2>
        <SiteForm initialSite={site} mode="edit" onSaved={onSaved} onCancel={onClose} />
      </div>
    </div>
  );
}

function SiteModal({ site, onClose }) {
  const docs = site.documents || {};
  const mapsUrl = site.latitude && site.longitude ? `https://www.google.com/maps?q=${site.latitude},${site.longitude}` : '';
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>×</button>
        <p className="eyebrow">OOH Site #{site.id}</p>
        <h2>{site.landlord_name}</h2>
        <div className="detail-grid">
          <Detail label="Hoarding Location" value={site.hoarding_location} />
          <Detail label="Landlord Location" value={site.landlord_location} />
          <Detail label="Landlord Phone" value={site.landlord_phone} />
          <Detail label="Landlord Email" value={site.landlord_email || '-'} />
          <Detail label="Secondary Contact" value={`${site.secondary_contact_name || '-'} ${site.secondary_contact_phone || ''}`} />
          <Detail label="Size" value={(site.size_boxes || []).length ? (site.size_boxes || []).map((box) => `${box.label || 'Size'}: ${box.width_ft} ft W × ${box.height_ft} ft H = ${box.area_sqft} sqft`).join(' | ') : `${site.width_ft} ft W × ${site.height_ft} ft H = ${site.area_sqft} sqft`} />
          <Detail label="Rental" value={site.rental_type} />
          <Detail label="Rent" value={formatCurrency(site.rent_amount)} />
          <Detail label="Advance" value={formatCurrency(site.advance_amount)} />
          <Detail label="Light" value={site.light_type} />
          <Detail label="Side" value={site.side_type} />
          <Detail label="Towards 1" value={site.towards_1 || '-'} />
          {site.side_type === 'Double' && <Detail label="Towards 2" value={site.towards_2 || '-'} />}
          <Detail label="GPS" value={mapsUrl ? <a href={mapsUrl} target="_blank" rel="noreferrer">Open in Google Maps</a> : '-'} />
          <Detail label="Agreement" value={`${site.agreement_tenure}: ${site.agreement_start_date} to ${site.agreement_end_date}`} />
          <Detail label="Agreement Status" value={site.agreement_status || (site.agreement_created ? 'Agreement Created' : 'Agreement Not Created')} />
          <Detail label="Agreement Created At" value={site.agreement_created_at ? formatDateTime(site.agreement_created_at) : '-'} />
          <Detail label="Uploaded On" value={formatDateTime(site.created_at)} />
          <Detail label="Last Updated" value={formatDateTime(site.updated_at)} />
          <Detail label="Entered By" value={site.created_by_name || '-'} />
        </div>
        <RemarksView remarks={site.remarks || {}} />
        <h3>Documents</h3>
        <div className="docs-list">
          <DocLink label="Site Photo" uploaded={docs.site_photo_uploaded} url={docs.site_photo_file_url} />
          <DocLink label="Landlord Photo" uploaded={docs.landlord_photo_uploaded} url={docs.landlord_photo_file_url} />
          <DocLink label="Aadhaar" uploaded={docs.aadhaar_uploaded} url={docs.aadhaar_file_url} />
          <DocLink label="PAN" uploaded={docs.pan_uploaded} url={docs.pan_file_url} />
          <DocLink label="Property Tax" uploaded={docs.property_tax_uploaded} url={docs.property_tax_file_url} />
          <DocLink label="Passbook" uploaded={docs.passbook_uploaded} url={docs.passbook_file_url} />
        </div>
      </div>
    </div>
  );
}

function RemarksView({ remarks }) {
  const entries = Object.entries(remarks || {}).filter(([, value]) => value);
  if (!entries.length) return null;
  return (
    <div className="remarks-view">
      <h3>Section Remarks</h3>
      <div className="detail-grid">
        {entries.map(([key, value]) => {
          const label = sectionRemarkLabels.find(([remarkKey]) => remarkKey === key)?.[1] || key;
          return <Detail key={key} label={`${label} Remark`} value={value} />;
        })}
      </div>
    </div>
  );
}

function Detail({ label, value }) {
  return <div className="detail"><span>{label}</span><strong>{value}</strong></div>;
}

function Users({ users, reloadUsers, currentUser }) {
  const emptyUserForm = { name: '', email: '', phone: '', password: '', role: 'employee', can_crud: true, is_active: true };
  const [form, setForm] = useState(emptyUserForm);
  const [editingUser, setEditingUser] = useState(null);
  const [deleteLoadingId, setDeleteLoadingId] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  function update(key, value) {
    setForm((prev) => {
      const next = { ...prev, [key]: value };
      if (key === 'role' && value === 'admin') next.can_crud = true;
      if (key === 'role' && value === 'employee' && editingUser?.role === 'admin') next.can_crud = true;
      return next;
    });
  }

  function startEdit(user) {
    setError('');
    setMessage('');
    setEditingUser(user);
    setForm({
      name: user.name || '',
      email: user.email || '',
      phone: user.phone || '',
      password: '',
      role: user.role || 'employee',
      can_crud: Boolean(user.can_crud),
      is_active: Boolean(user.is_active),
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function cancelEdit() {
    setEditingUser(null);
    setForm(emptyUserForm);
    setError('');
  }

  async function toggleCrudPermission(user) {
    setError('');
    setMessage('');
    try {
      await apiFetch(`/api/users/${user.id}/crud-permission`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ can_crud: !user.can_crud }),
      });
      await reloadUsers();
      setMessage(`${user.name}'s CRUD permission updated.`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function deleteUser(user) {
    setError('');
    setMessage('');
    if (user.id === currentUser?.id) {
      setError('You cannot delete your own admin account.');
      return;
    }
    const ok = window.confirm(`Delete or deactivate ${user.name}? If this user has submitted OOH records, the account will be deactivated to preserve old records.`);
    if (!ok) return;
    setDeleteLoadingId(user.id);
    try {
      const result = await apiFetch(`/api/users/${user.id}`, { method: 'DELETE' });
      await reloadUsers();
      setMessage(result.message || 'User updated successfully.');
      if (editingUser?.id === user.id) cancelEdit();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleteLoadingId(null);
    }
  }

  async function submit(e) {
    e.preventDefault();
    setMessage('');
    setError('');
    const payload = {
      ...form,
      email: form.email.trim().toLowerCase(),
      role: form.role,
      can_crud: form.role === 'admin' ? true : Boolean(form.can_crud),
      is_active: Boolean(form.is_active),
    };
    if (!editingUser && !payload.password) {
      setError('Password is required for new users.');
      return;
    }
    if (editingUser && !payload.password) delete payload.password;
    try {
      await apiFetch(editingUser ? `/api/users/${editingUser.id}` : '/api/users', {
        method: editingUser ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      setMessage(editingUser ? 'Employee details updated successfully.' : 'Employee login created successfully.');
      setForm(emptyUserForm);
      setEditingUser(null);
      await reloadUsers();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="page-stack">
      <div className="form-section">
        <div className="section-title">
          <span>{editingUser ? '✎' : '+'}</span>
          <div>
            <h2>{editingUser ? `Edit Employee / User #${editingUser.id}` : 'Create Employee / User'}</h2>
            <p>Admin can create, update, deactivate/delete employees and control CRUD permission.</p>
          </div>
        </div>
        {message && <div className="alert success">{message}</div>}
        {error && <div className="alert error">{error}</div>}
        <form className="grid five user-form" onSubmit={submit}>
          <Field label="Name" required><input value={form.name} onChange={(e) => update('name', e.target.value)} required /></Field>
          <Field label="Email" required><input type="email" value={form.email} onChange={(e) => update('email', e.target.value)} required /></Field>
          <Field label="Phone"><input value={form.phone} onChange={(e) => update('phone', e.target.value)} /></Field>
          <Field label={editingUser ? 'New Password (optional)' : 'Password'} required={!editingUser}>
            <input type="password" value={form.password} onChange={(e) => update('password', e.target.value)} required={!editingUser} placeholder={editingUser ? 'Leave blank to keep current password' : 'Minimum 6 characters'} />
          </Field>
          <Field label="Role" required>
            <select value={form.role} onChange={(e) => update('role', e.target.value)}>
              <option value="employee">employee</option>
              <option value="admin">admin</option>
            </select>
          </Field>
          <label className="permission-check">
            <input type="checkbox" checked={Boolean(form.is_active)} disabled={editingUser?.id === currentUser?.id} onChange={(e) => update('is_active', e.target.checked)} />
            Active Login
          </label>
          <label className="permission-check">
            <input type="checkbox" checked={Boolean(form.can_crud)} disabled={form.role === 'admin'} onChange={(e) => update('can_crud', e.target.checked)} />
            Allow OOH CRUD
          </label>
          <div className="user-form-actions">
            {editingUser && <button className="ghost-btn" type="button" onClick={cancelEdit}>Cancel Edit</button>}
            <button className="primary-btn" type="submit">{editingUser ? 'Update User' : 'Create User'}</button>
          </div>
        </form>
      </div>

      <div className="panel">
        <h2>Employee / User Management</h2>
        <p className="muted">Deleting a user with existing OOH submissions will deactivate the login instead of removing history, so old records remain properly linked.</p>
        <div className="user-list">
          {users.map((user) => (
            <div className="user-row user-row-crud" key={user.id}>
              <strong>{user.name}</strong>
              <span>{user.email}</span>
              <span>{user.phone || '-'}</span>
              <em>{user.role}</em>
              <span className={user.is_active ? 'permission-badge allowed' : 'permission-badge blocked'}>{user.is_active ? 'Active' : 'Blocked'}</span>
              <span className={user.can_crud ? 'permission-badge allowed' : 'permission-badge blocked'}>{user.can_crud ? 'CRUD Allowed' : 'CRUD Blocked'}</span>
              <div className="user-row-actions">
                <button className="secondary-btn" onClick={() => startEdit(user)}>Edit</button>
                {user.role === 'employee' && (
                  <button className={user.can_crud ? 'danger-btn' : 'secondary-btn'} onClick={() => toggleCrudPermission(user)}>
                    {user.can_crud ? 'Block CRUD' : 'Allow CRUD'}
                  </button>
                )}
                <button className="danger-btn" onClick={() => deleteUser(user)} disabled={deleteLoadingId === user.id || user.id === currentUser?.id}>
                  {deleteLoadingId === user.id ? 'Deleting...' : user.id === currentUser?.id ? 'Current User' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [user, setUser] = useState(getStoredUser());
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sites, setSites] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(Boolean(getToken()));
  const [error, setError] = useState('');

  async function loadSites() {
    try {
      const data = await apiFetch('/api/sites');
      setSites(data);
    } catch (err) {
      setError(err.message);
      if (err.message.toLowerCase().includes('token')) handleLogout();
    }
  }

  async function loadUsers() {
    if (user?.role !== 'admin') return;
    try {
      const data = await apiFetch('/api/users');
      setUsers(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function bootstrap() {
    setLoading(true);
    setError('');
    try {
      if (getToken()) {
        const me = await apiFetch('/api/users/me');
        setUser(me);
        localStorage.setItem('ooh_user', JSON.stringify(me));
        await loadSites();
      }
    } catch (err) {
      setError(err.message);
      clearSession();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    clearSession();
    setUser(null);
    setSites([]);
    setUsers([]);
  }

  useEffect(() => {
    bootstrap();
  }, []);

  useEffect(() => {
    if (user?.role === 'admin') loadUsers();
  }, [user?.role]);

  if (!user) return <Login onLogin={(loggedInUser) => { setUser(loggedInUser); loadSites(); }} />;

  return (
    <div className="app-shell">
      <Header user={user} activeTab={activeTab} setActiveTab={setActiveTab} onLogout={handleLogout} />
      <main className="content">
        {error && <div className="alert error">{error}</div>}
        {loading && <div className="empty-state">Loading...</div>}
        {!loading && activeTab === 'dashboard' && <Dashboard sites={sites} />}
        {!loading && activeTab === 'add' && <SiteForm onCreated={loadSites} />}
        {!loading && activeTab === 'records' && <Records sites={sites} reload={loadSites} user={user} />}
        {!loading && activeTab === 'users' && user.role === 'admin' && <Users users={users} reloadUsers={loadUsers} currentUser={user} />}
      </main>
    </div>
  );
}
