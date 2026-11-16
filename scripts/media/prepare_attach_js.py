import base64
from pathlib import Path

p = Path(r"d:\Projects\Digital Wellbeing\thumbnail_refs\reference_real_notch_ui.png")
b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
print("Base64 length:", len(b64))

out_js = Path(r"C:\Users\akshi\.gemini\antigravity-ide\brain\04ef7153-e3f8-4ae5-adad-b6e2eed620f7\browser\attach_ref.js")
js_code = f"""(async () => {{
  const b64 = "{b64}";
  const bin = atob(b64);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  const file = new File([u8], 'real_notch_ui_reference.png', {{ type: 'image/png' }});
  const dt = new DataTransfer();
  dt.items.add(file);
  const input = document.querySelector('#upload-files') || document.querySelector('input[type="file"]');
  input.files = dt.files;
  input.dispatchEvent(new Event('change', {{ bubbles: true }}));
  return {{ success: true, fileName: file.name, fileSize: file.size }};
}})();"""

out_js.write_text(js_code, encoding="utf-8")
print(f"Saved attach_ref.js: {out_js.stat().st_size} bytes")
