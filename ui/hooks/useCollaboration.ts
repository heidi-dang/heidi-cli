import { useState, useEffect, useRef, useCallback } from 'react';

export interface Peer {
  id: string;
  isTyping?: boolean;
  stream?: MediaStream;
}

export const useCollaboration = (roomId: string | null) => {
  const [peers, setPeers] = useState<Peer[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  
  const roomRef = useRef<any>(null);
  const actionsRef = useRef<any>(null);

  // Initialize Room
  useEffect(() => {
    if (!roomId) return;

    let cleanup = () => {};

    const init = async () => {
      try {
        // Dynamic import from esm.sh
        const { joinRoom, selfId } = await import('https://esm.sh/trystero@0.19.0/torrent');
        
        const config = { appId: 'heidi-gemini-studio-v1' };
        const room = joinRoom(config, roomId);
        roomRef.current = room;

        // Actions
        const [sendMsg, getMsg] = room.makeAction('message');
        const [sendTyping, getTyping] = room.makeAction('typing');
        actionsRef.current = { sendMsg, sendTyping };

        // Handlers
        getMsg((data: any, peerId: string) => {
          setMessages(prev => [...prev, { ...data, senderId: peerId, isRemote: true }]);
        });

        getTyping((isTyping: boolean, peerId: string) => {
          if (isTyping) {
            setTypingUsers(prev => Array.from(new Set([...prev, peerId])));
          } else {
            setTypingUsers(prev => prev.filter(id => id !== peerId));
          }
        });

        room.onPeerJoin((peerId: string) => {
          setPeers(prev => [...prev, { id: peerId }]);
          console.log(`${peerId} joined`);
        });

        room.onPeerLeave((peerId: string) => {
          setPeers(prev => prev.filter(p => p.id !== peerId));
          setTypingUsers(prev => prev.filter(id => id !== peerId));
          console.log(`${peerId} left`);
        });

        room.onPeerStream((stream: MediaStream, peerId: string) => {
          setPeers(prev => prev.map(p => p.id === peerId ? { ...p, stream } : p));
        });

        cleanup = () => {
          room.leave();
          roomRef.current = null;
        };

      } catch (e) {
        console.error("Failed to init collaboration", e);
      }
    };

    init();

    return () => {
      cleanup();
      if (localStream) {
        localStream.getTracks().forEach(t => t.stop());
      }
    };
  }, [roomId]);

  // Messaging
  const broadcastMessage = useCallback((text: string, attachment?: any) => {
    if (actionsRef.current) {
        const msg = { text, attachment, timestamp: Date.now() };
        actionsRef.current.sendMsg(msg);
        // Add to own local list
        // setMessages(prev => [...prev, { ...msg, isRemote: false }]); 
        // Logic handled by parent usually, but we can return it
    }
  }, []);

  const broadcastTyping = useCallback((isTyping: boolean) => {
     if (actionsRef.current) {
         actionsRef.current.sendTyping(isTyping);
     }
  }, []);

  // Media
  const startCall = useCallback(async (video = true, audio = true) => {
    if (!roomRef.current) return;
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video, audio });
        setLocalStream(stream);
        roomRef.current.addStream(stream);
    } catch (e) {
        console.error("Failed to access media", e);
    }
  }, []);

  const endCall = useCallback(() => {
      if (localStream) {
          localStream.getTracks().forEach(t => t.stop());
          setLocalStream(null);
          if (roomRef.current) {
            // Trystero removeStream api is implicit often by track stop, or specific api depending on version
            // For now, removing the stream from state handles UI
             roomRef.current.removeStream(localStream);
          }
      }
  }, [localStream]);

  return {
    peers,
    messages,
    typingUsers,
    localStream,
    broadcastMessage,
    broadcastTyping,
    startCall,
    endCall
  };
};