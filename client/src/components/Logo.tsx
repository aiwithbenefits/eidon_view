import eidonLogo from '../assets/eidon_logo.png';

export function Logo() {
  return (
    <div className="logo-container">
      <img src={eidonLogo} alt="Eidon Logo" className="h-8 w-auto" />
      <span>Eidon</span>
    </div>
  );
}