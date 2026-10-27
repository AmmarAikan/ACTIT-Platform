interface BrandMarkProps {
  withText?: boolean;
}

export function BrandMark({ withText = false }: BrandMarkProps) {
  if (withText) {
    return (
      <span className="brand-lockup" aria-hidden="true">
        <img className="brand-lockup-symbol" src="/branding/actit-logo.webp" alt="" />
        <span className="brand-lockup-copy">
          <strong>ACTIT</strong>
          <small>AI-Assisted Threat Intelligence</small>
        </span>
      </span>
    );
  }

  return (
    <span className="brand-mark" aria-hidden="true">
      <img
        className="brand-symbol-image"
        src="/branding/actit-logo.webp"
        alt=""
      />
    </span>
  );
}
