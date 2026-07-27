
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./components/AnimatedHome";
import About from "./components/About";
import WhyChooseUs from "./components/WhyChooseUs";
import Services from "./components/Services";
import Testimonials from "./components/Testimonials";
import Contact from "./components/Contact";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";
import VerifyEmail from "./pages/VerifyEmail";
import NIDVerification from "./pages/NIDVerification";
import ProfilePage from "./pages/ProfilePage";
import FindMatches from "./pages/FindMatches";
import Notifications from "./pages/Notifications";
import InterestRequests from "./pages/InterestRequests";
import Messages from "./pages/Messages";
import FullProfileView from "./pages/FullProfileView";
import { AuthProvider } from "./context/AuthContext";
import { AdminProvider } from "./context/AdminContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminProtectedRoute from "./components/AdminProtectedRoute";
import AdminLogin from "./pages/AdminLogin";
import AdminDashboard from "./pages/AdminDashboard";
import Layout from "./components/Layout";

function App(): JSX.Element {
  return (
    <AuthProvider>
      <AdminProvider>
        <Router>
          <Routes>
            {/* Admin Routes - No navbar/footer */}
            <Route path="/admin-login" element={<AdminLogin />} />
            <Route path="/admin-dashboard" element={
              <AdminProtectedRoute>
                <AdminDashboard />
              </AdminProtectedRoute>
            } />

            {/* Regular App Routes with Layout */}
            <Route path="/" element={<Layout><Home /></Layout>} />
            <Route path="/about" element={<Layout><About /></Layout>} />
            <Route path="/why-choose-us" element={<Layout><WhyChooseUs /></Layout>} />
            <Route path="/services" element={<Layout><Services /></Layout>} />
            <Route path="/testimonials" element={<Layout><Testimonials /></Layout>} />
            <Route path="/contact" element={<Layout><Contact /></Layout>} />
            <Route path="/signin" element={<Layout><SignIn /></Layout>} />
            <Route path="/signup" element={<Layout><SignUp /></Layout>} />
            <Route path="/verify-email" element={<Layout><VerifyEmail /></Layout>} />
            
            <Route path="/nid-verification" element={
              <ProtectedRoute>
                <Layout><NIDVerification /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/profile" element={
              <ProtectedRoute>
                <Layout><ProfilePage /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/find-matches" element={
              <ProtectedRoute>
                <Layout><FindMatches /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/interest-requests" element={
              <ProtectedRoute>
                <Layout><InterestRequests /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/messages" element={
              <ProtectedRoute>
                <Layout><Messages /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/profiles/:userId/full" element={
              <ProtectedRoute>
                <Layout><FullProfileView /></Layout>
              </ProtectedRoute>
            } />
            
            {/* Direct access routes for development */}
            <Route path="/matches" element={<Layout><FindMatches /></Layout>} />
            <Route path="/notifications" element={<Layout><Notifications /></Layout>} />
            <Route path="/interests" element={<Layout><InterestRequests /></Layout>} />
            <Route path="/chat" element={<Layout><Messages /></Layout>} />
            <Route path="/verify" element={<Layout><NIDVerification /></Layout>} />
          </Routes>
        </Router>
      </AdminProvider>
    </AuthProvider>
  );
}

export default App;
