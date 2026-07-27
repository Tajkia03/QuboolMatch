import React from 'react';
import { Phone, Mail, MessageCircle, HeadphonesIcon } from 'lucide-react';

const Contact = () => {
  return (
    <section id="contact" className="py-20 bg-gradient-to-br from-gray-900 to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-4xl lg:text-5xl font-bold text-white mb-6">
            Get in <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 to-pink-400">Touch</span>
          </h2>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto leading-relaxed">
            We're here to help you on your journey to finding love. Reach out to us anytime for support, 
            guidance, or any questions you may have.
          </p>
        </div>

        <div className="mx-auto max-w-2xl">
          {/* Contact Information */}
          <div className="space-y-8">
            <h3 className="text-center text-2xl font-bold text-white mb-8">Contact Information</h3>
            
            {/* Helpline - Featured */}
            <div className="bg-gradient-to-r from-emerald-600 to-emerald-500 rounded-2xl p-6">
              <div className="flex items-center space-x-4">
                <div className="bg-white/20 p-3 rounded-xl">
                  <HeadphonesIcon className="h-8 w-8 text-white" />
                </div>
                <div>
                  <h4 className="text-xl font-bold text-white">24/7 Helpline</h4>
                  <p className="text-emerald-100 text-lg font-semibold">01522434565</p>
                  <p className="text-emerald-100 text-sm">Always available for your support</p>
                </div>
              </div>
            </div>

            {/* Other Contact Methods */}
            <div className="space-y-6">
              <div className="flex items-center space-x-4 bg-gray-800 rounded-xl p-6">
                <div className="bg-blue-600 p-3 rounded-xl">
                  <Phone className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h4 className="font-semibold text-white">Phone Support</h4>
                  <p className="text-gray-300">01522434565</p>
                </div>
              </div>

              <div className="flex items-center space-x-4 bg-gray-800 rounded-xl p-6">
                <div className="bg-rose-600 p-3 rounded-xl">
                  <Mail className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h4 className="font-semibold text-white">Email Support</h4>
                  <p className="text-gray-300">support@quboolmatch.com</p>
                </div>
              </div>

              

             
            </div>
          </div>
        </div>

        {/* Emergency Contact */}
        <div className="mt-16 text-center">
          <div className="bg-red-600 rounded-2xl p-6 inline-block">
            <div className="flex items-center space-x-3">
              <MessageCircle className="h-6 w-6 text-white" />
              <div className="text-left">
                <h4 className="text-white font-bold">Emergency Support</h4>
                <p className="text-red-100 text-sm">For urgent safety concerns: <span className="font-semibold">01522434565</span></p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Contact;
