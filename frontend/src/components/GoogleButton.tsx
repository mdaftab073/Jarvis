import { useEffect, useRef, useState } from 'react';

declare global {
  interface Window {
    google?: any;
  }
}

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

// Prevent multiple initializations in React StrictMode
let googleInitialized = false;

function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve();
      return;
    }

    const existingScript = document.querySelector(
      'script[src="https://accounts.google.com/gsi/client"]'
    );

    if (existingScript) {
      existingScript.addEventListener('load', () => resolve());
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;

    script.onload = () => resolve();

    script.onerror = () =>
      reject(
        new Error(
          'Google sign-in could not load. Check your connection or ad blocker.'
        )
      );

    document.head.appendChild(script);
  });
}

interface GoogleButtonProps {
  onToken: (token: string) => void;
  onError: (message: string) => void;
}

export function GoogleButton({
  onToken,
  onError,
}: GoogleButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRendered = useRef(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let mounted = true;

    if (!CLIENT_ID) {
      onError('Set VITE_GOOGLE_CLIENT_ID in .env to enable sign-in.');
      return;
    }

    loadScript()
      .then(() => {
        if (!mounted || !containerRef.current) return;

        // Initialize Google Identity Services only once
        if (!googleInitialized) {
          window.google.accounts.id.initialize({
            client_id: CLIENT_ID,
            callback: (response: any) => {
              if (response?.credential) {
                onToken(response.credential);
              } else {
                onError('Google did not return a credential.');
              }
            },
          });

          googleInitialized = true;
        }

        // Render button only once per component instance
        if (!buttonRendered.current && containerRef.current) {
          containerRef.current.innerHTML = '';

          window.google.accounts.id.renderButton(
            containerRef.current,
            {
              theme: 'outline',
              size: 'large',
              text: 'signin_with',
              width: 280,
            }
          );

          buttonRendered.current = true;
        }

        if (mounted) {
          setReady(true);
        }
      })
      .catch((error) => {
        if (mounted) {
          onError(
            error instanceof Error
              ? error.message
              : 'Google sign-in initialization failed.'
          );
        }
      });

    return () => {
      mounted = false;
    };
  }, [onToken, onError]);

  return (
    <div
      ref={containerRef}
      aria-label="Sign in with Google"
      style={{ minHeight: 44 }}
    />
  );
}