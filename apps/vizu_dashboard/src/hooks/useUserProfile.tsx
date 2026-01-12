import { useEffect, useState } from 'react';
import { useAuth } from './useAuth';

export interface UserProfile {
  full_name: string;
  email: string;
  initials: string;
  isAdmin: boolean;
}

/**
 * Custom hook to get user profile information with proper fallbacks
 */
export const useUserProfile = (): UserProfile | null => {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    if (!user) {
      setProfile(null);
      return;
    }

    // Get full name from metadata or derive from email
    const fullName =
      user.user_metadata?.full_name ||
      user.user_metadata?.name ||
      user.email?.split('@')[0] ||
      'Usuário';

    // Calculate initials
    const initials = fullName
      .split(' ')
      .map((n: string) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);

    // Check admin status
    const isAdmin =
      user.user_metadata?.role === 'admin' ||
      user.app_metadata?.role === 'admin' ||
      false;

    setProfile({
      full_name: fullName,
      email: user.email || 'Sem email',
      initials,
      isAdmin,
    });
  }, [user]);

  return profile;
};

export default useUserProfile;
