import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Heart, Facebook, Twitter, Instagram, Youtube, Mail, Phone } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Footer = () => {
  const { isLoggedIn } = useAuth();
  const location = useLocation();
  const showAdminLink = location.pathname === '/' && !isLoggedIn;

  return (
    <footer className="bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid lg:grid-cols-4 gap-12">
          {/* Brand Section */}
          <div className="lg:col-span-1">
            <div className="flex items-center space-x-2 mb-6">
              <div className="bg-gradient-to-br from-rose-500 to-pink-600 p-2 rounded-xl">
                <Heart className="h-6 w-6 text-white" fill="currentColor" />
              </div>
              <span className="text-2xl font-bold text-white">Qubool Match</span>
            </div>
            <p className="text-gray-300 leading-relaxed mb-6">
              Ethical matrimonial platform dedicated to helping you find your perfect life partner 
              through safe, respectful, and meaningful connections.
            </p>
            <div className="flex space-x-4">
              <a href="#" className="bg-gray-800 p-3 rounded-xl hover:bg-rose-600 transition-colors duration-300">
                <Facebook className="h-5 w-5" />
              </a>
              <a href="#" className="bg-gray-800 p-3 rounded-xl hover:bg-blue-500 transition-colors duration-300">
                <Twitter className="h-5 w-5" />
              </a>
              <a href="#" className="bg-gray-800 p-3 rounded-xl hover:bg-pink-600 transition-colors duration-300">
                <Instagram className="h-5 w-5" />
              </a>
              <a href="#" className="bg-gray-800 p-3 rounded-xl hover:bg-red-600 transition-colors duration-300">
                <Youtube className="h-5 w-5" />
              </a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-xl font-bold mb-6">Quick Links</h3>
            <ul className="space-y-3">
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Home</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">About Us</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">How It Works</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Success Stories</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Pricing</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Blog</a></li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h3 className="text-xl font-bold mb-6">Support</h3>
            <ul className="space-y-3">
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Help Center</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Safety Guidelines</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Privacy Policy</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Terms of Service</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Community Guidelines</a></li>
              <li><a href="#" className="text-gray-300 hover:text-white transition-colors duration-200">Report Issues</a></li>
            </ul>
          </div>

          {/* Contact Info */}
          <div>
            <h3 className="text-xl font-bold mb-6">Contact Info</h3>
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <Phone className="h-5 w-5 text-rose-400" />
                <div>
                  <div className="text-white font-semibold">01522434565</div>
                  <div className="text-gray-400 text-sm">24/7 Helpline</div>
                </div>
              </div>
              
              <div className="flex items-center space-x-3">
                <Mail className="h-5 w-5 text-rose-400" />
                <div>
                  <div className="text-white">support@quboolmatch.com</div>
                  <div className="text-gray-400 text-sm">Email Support</div>
                </div>
              </div>
              
            
            </div>

            {/* Emergency Contact */}
            <div className="mt-8 bg-red-600/20 border border-red-500/30 rounded-xl p-4">
              <h4 className="text-red-400 font-bold mb-2">Emergency Support</h4>
              <p className="text-red-300 text-sm">
                For urgent safety concerns:
                <span className="block font-semibold text-red-200">01522434565</span>
              </p>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-gray-700 mt-16 pt-8">
          <div className="flex flex-col lg:flex-row justify-between items-center space-y-4 lg:space-y-0">
            <div className="text-gray-400 text-sm">
              © 2024 Qubool Match. All rights reserved. | Committed to ethical matrimonial services.
            </div>
            <div className="flex items-center space-x-6 text-sm text-gray-400">
              <a href="#" className="hover:text-white transition-colors duration-200">Privacy Policy</a>
              <a href="#" className="hover:text-white transition-colors duration-200">Terms of Service</a>
              <a href="#" className="hover:text-white transition-colors duration-200">Safety Center</a>
              {showAdminLink && (
                <Link to="/admin-login" className="text-xs text-gray-500 hover:text-gray-300 transition-colors duration-200">
                  Admin
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
