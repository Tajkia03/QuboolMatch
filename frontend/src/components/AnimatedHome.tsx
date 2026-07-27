import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import About from './About';
import Services from './Services';
import WhyChooseUs from './WhyChooseUs';
import Testimonials from './Testimonials';
import Contact from './Contact';
import SignupSuccessNotification from './SignupSuccessNotification';

const AnimatedHome: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('home-section-visible');
          observer.unobserve(entry.target);
        }
      }),
      { threshold: 0.12 },
    );
    document.querySelectorAll('.home-animated-section').forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!location.hash) return;
    window.setTimeout(() => {
      document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 40);
  }, [location.hash]);

  return (
    <main className="overflow-hidden bg-[#fffaf6] text-[#342a28]">
      <SignupSuccessNotification />
      <section id="home" className="relative flex min-h-[720px] scroll-mt-20 items-center overflow-hidden bg-gradient-to-br from-[#fffaf6] to-[#faeee9] py-16">
        <div className="home-drift absolute -right-20 top-12 h-64 w-64 rounded-full bg-[#efc8cf]/60" />
        <div className="home-drift-delayed absolute bottom-8 left-[45%] h-28 w-28 rounded-full bg-[#ebd2bd]/70" />
        <div className="relative z-10 mx-auto grid w-full max-w-7xl items-center gap-14 px-5 lg:grid-cols-[1.08fr_.92fr] lg:px-8">
          <div className="home-hero-enter">
            <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-[#a83f62]">Verified · Respectful · Meaningful</p>
            <h1 className="mt-4 max-w-3xl font-serif text-5xl font-bold leading-[0.98] tracking-[-0.045em] sm:text-6xl lg:text-7xl">
              Where sincere hearts find their <span className="home-title-mark text-[#a83f62]">Qubool.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-[#756762] sm:text-lg">
              Thoughtful matrimonial matching for people seeking commitment, shared values, and a meaningful beginning.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link to="/signup" className="home-lift rounded-xl bg-[#a83f62] px-6 py-3 font-bold text-white shadow-lg shadow-rose-900/15">Create your profile</Link>
              <a href="#about" className="home-lift rounded-xl bg-[#f5e4e9] px-6 py-3 font-bold text-[#7b3650]">See how it works</a>
            </div>
            <div className="mt-8 flex flex-wrap gap-5 text-sm text-[#6c605c]">
              <span>✓ NID verified</span><span>✓ Privacy-first</span><span>✓ Compatibility matching</span>
            </div>
          </div>
          <div className="relative mx-auto h-[390px] w-full max-w-md lg:h-[510px]">
            <div className="home-float absolute inset-x-5 inset-y-3 rounded-t-[190px] rounded-b-3xl bg-gradient-to-br from-[#b76572] to-[#e0a080] shadow-[28px_30px_0_#f0d8ce]">
              <span className="grid h-full place-items-center font-serif text-9xl font-bold text-white/40">Q</span>
            </div>
            <div className="home-float-delayed absolute bottom-14 left-0 rounded-2xl border border-white/70 bg-white/95 p-4 shadow-2xl shadow-rose-950/15">
              <b className="block text-[#a83f62]">92% compatible</b>
              <small className="text-[#766a66]">Values · Lifestyle · Family</small>
            </div>
          </div>
        </div>
      </section>

      <div className="overflow-hidden bg-[#45313b] py-3.5 text-white">
        <div className="home-ticker flex w-max text-xs tracking-wide">
          {[...Array(2)].flatMap((_, index) => [
            <span key={`${index}-verified`} className="px-9">✦ VERIFIED PROFILES</span>,
            <span key={`${index}-connections`} className="px-9">♡ MEANINGFUL CONNECTIONS</span>,
            <span key={`${index}-privacy`} className="px-9">✦ PRIVACY-FIRST MATCHING</span>,
            <span key={`${index}-community`} className="px-9">♡ RESPECTFUL COMMUNITY</span>,
          ])}
        </div>
      </div>

      <div className="home-animated-section scroll-mt-20"><About /></div>
      <div className="home-animated-section scroll-mt-20"><Services /></div>
      <div className="home-animated-section scroll-mt-20"><WhyChooseUs /></div>
      <div id="testimonials" className="home-animated-section scroll-mt-20"><Testimonials /></div>
      <div className="home-animated-section scroll-mt-20"><Contact /></div>
    </main>
  );
};

export default AnimatedHome;
