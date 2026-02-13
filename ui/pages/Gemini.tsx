import React, { useState, useRef, useEffect } from 'react';
import { ai, checkApiKeySelection } from '../api/gemini';
import { GenerateContentResponse, Modality, LiveServerMessage } from '@google/genai';
import { PanelLeft, Mic, Send, Image as ImageIcon, Video, Wand2, Sparkles, Loader2, Volume2, Search, MapPin, Play, StopCircle, RefreshCw, Upload, Download, Users, Phone, PhoneOff, Video as VideoIcon } from 'lucide-react';
import { useCollaboration, Peer } from '../hooks/useCollaboration';

interface GeminiProps {
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
}

type Tab = 'chat' | 'create' | 'live';
type CreateMode = 'image' | 'video' | 'edit';
type ChatMessage = { 
    role: 'user' | 'model' | 'peer'; 
    text: string; 
    audio?: string; 
    image?: string; 
    video?: string; 
    mimeType?: string;
    isThinking?: boolean;
    senderId?: string; // For peers
};

export default function Gemini({ isSidebarOpen, onToggleSidebar }: GeminiProps) {
  const [activeTab, setActiveTab] = useState<Tab>('chat');

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [prompt, setPrompt] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [isFast, setIsFast] = useState(false);
  const [useSearch, setUseSearch] = useState(false);
  const [useMaps, setUseMaps] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [attachment, setAttachment] = useState<{ type: 'image' | 'video'; data: string; mimeType: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Collaboration State
  const [collabRoomId, setCollabRoomId] = useState('');
  const [activeRoom, setActiveRoom] = useState<string | null>(null);
  const { peers, messages: remoteMessages, typingUsers, broadcastMessage, broadcastTyping, startCall, endCall, localStream } = useCollaboration(activeRoom);
  const [isInCall, setIsInCall] = useState(false);

  // Create State
  const [createMode, setCreateMode] = useState<CreateMode>('image');
  const [createPrompt, setCreatePrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('1:1');
  const [imageSize, setImageSize] = useState('1K');
  const [generatedMedia, setGeneratedMedia] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [referenceImage, setReferenceImage] = useState<{ data: string; mimeType: string } | null>(null);

  // Live State
  const [isLiveConnected, setIsLiveConnected] = useState(false);
  const [liveStatus, setLiveStatus] = useState('Disconnected');
  const [liveVolume, setLiveVolume] = useState(0);

  // Sync Remote Messages
  useEffect(() => {
      if (remoteMessages.length > 0) {
          const lastMsg = remoteMessages[remoteMessages.length - 1];
          // Check if we already have this message (simple dedup by timestamp/content if needed, but here just append)
          // Ideally we'd have IDs. For now, we trust the stream.
          const newMsg: ChatMessage = {
              role: 'peer',
              text: lastMsg.text,
              senderId: lastMsg.senderId,
              image: lastMsg.attachment?.type === 'image' ? lastMsg.attachment.data : undefined,
              video: lastMsg.attachment?.type === 'video' ? lastMsg.attachment.data : undefined,
              mimeType: lastMsg.attachment?.mimeType
          };
          setMessages(prev => [...prev, newMsg]);
      }
  }, [remoteMessages]);

  // Typing Broadcast
  const handleTyping = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setPrompt(e.target.value);
      if (activeRoom) {
          broadcastTyping(true);
          // Debounce stop typing
          const timeout = setTimeout(() => broadcastTyping(false), 2000);
          return () => clearTimeout(timeout);
      }
  };

  // --- Chat Logic ---

  const handleSendMessage = async () => {
    if (!prompt.trim() && !attachment) return;

    // Capture attachment in local scope before state clear
    const currentAttachment = attachment;

    const userMsg: ChatMessage = { role: 'user', text: prompt };
    if (currentAttachment) {
      if (currentAttachment.type === 'image') {
          userMsg.image = currentAttachment.data;
          userMsg.mimeType = currentAttachment.mimeType;
      }
      if (currentAttachment.type === 'video') {
          userMsg.video = currentAttachment.data;
          userMsg.mimeType = currentAttachment.mimeType;
      }
    }
    
    setMessages(prev => [...prev, userMsg]);
    
    // Broadcast if in room
    if (activeRoom) {
        broadcastMessage(prompt, currentAttachment);
    }

    setPrompt('');
    setAttachment(null);
    setIsProcessing(true);

    // If it's a peer command (optional), we might skip AI? 
    // But typically user wants AI + Peer.
    // We proceed to call Gemini.

    try {
      let model = 'gemini-3-pro-preview';
      let config: any = {};

      // Determine model based on flags and attachment
      if (isFast) {
        model = 'gemini-2.5-flash-lite';
      } else if (isThinking) {
        model = 'gemini-3-pro-preview';
        config.thinkingConfig = { thinkingBudget: 32768 };
      } else if (useSearch) {
        model = 'gemini-3-flash-preview';
        config.tools = [{ googleSearch: {} }];
      } else if (useMaps) {
        model = 'gemini-2.5-flash';
        config.tools = [{ googleMaps: {} }];
      } else if (currentAttachment && currentAttachment.type === 'video') {
         model = 'gemini-3-pro-preview'; // Video understanding
      } else if (currentAttachment && currentAttachment.type === 'image') {
         model = 'gemini-3-pro-preview'; // Image understanding
      }

      // Prepare contents
      let contents: any = { parts: [{ text: userMsg.text }] };
      if (userMsg.image) {
        contents.parts.unshift({ inlineData: { data: userMsg.image, mimeType: userMsg.mimeType || 'image/jpeg' } });
      }
      if (userMsg.video) {
        // For inline video (limitations apply to size, usually < 20MB for inline)
        contents.parts.unshift({ inlineData: { data: userMsg.video, mimeType: userMsg.mimeType || 'video/mp4' } });
      }

      // Check key for Pro models if needed
      if (model.includes('pro-preview')) await checkApiKeySelection();

      const response = await ai.models.generateContent({
        model,
        contents,
        config
      });

      const text = response.text || "No text response.";
      
      // Check for grounding
      let groundingInfo = '';
      if (response.candidates?.[0]?.groundingMetadata?.groundingChunks) {
         groundingInfo = "\n\nSources:\n" + response.candidates[0].groundingMetadata.groundingChunks
            .map((c: any) => c.web?.uri || c.maps?.uri).filter(Boolean).join('\n');
      }

      const aiMsg: ChatMessage = { role: 'model', text: text + groundingInfo };
      setMessages(prev => [...prev, aiMsg]);
      
      // Optionally broadcast AI response to peers? 
      // Usually peers run their own AI or see user prompt. 
      // Let's NOT broadcast AI response to avoid double-generation display on peers if they also had logic.
      // But if we want shared AI state, we would broadcast it.
      // For this "Chat in same room" request, assuming human chat + individual AI or shared context.
      // We will broadcast the AI response so peers see what AI said to ME.
      if (activeRoom) {
          // Send as a special system message or just text
          broadcastMessage(`[AI Response]: ${text + groundingInfo}`);
      }

    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'model', text: `Error: ${e.message}` }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTranscribe = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        const audioChunks: Blob[] = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = async () => {
                const base64Audio = (reader.result as string).split(',')[1];
                setIsProcessing(true);
                try {
                     const response = await ai.models.generateContent({
                        model: 'gemini-3-flash-preview',
                        contents: {
                            parts: [
                                { inlineData: { mimeType: 'audio/wav', data: base64Audio } },
                                { text: "Transcribe this audio exactly." }
                            ]
                        }
                    });
                    setPrompt(prev => prev + " " + (response.text || ""));
                } catch (e) {
                    console.error(e);
                } finally {
                    setIsProcessing(false);
                }
            };
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        setLiveStatus("Recording...");
        setTimeout(() => {
            mediaRecorder.stop();
            setLiveStatus("Disconnected");
        }, 5000); // Record for 5 seconds for simple test
    } catch (e) {
        console.error("Mic permission denied", e);
    }
  };

  const handleTTS = async (text: string) => {
    try {
        const response = await ai.models.generateContent({
            model: "gemini-2.5-flash-preview-tts",
            contents: [{ parts: [{ text }] }],
            config: {
                responseModalities: [Modality.AUDIO],
                speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } } },
            },
        });
        const base64 = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
        if (base64) {
            const audio = new Audio(`data:audio/wav;base64,${base64}`);
            audio.play();
        }
    } catch (e) {
        console.error("TTS Failed", e);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1];
          setAttachment({
              type: file.type.startsWith('video') ? 'video' : 'image',
              data: base64,
              mimeType: file.type
          });
      };
      reader.readAsDataURL(file);
  };

  // --- Create Logic ---

  const handleCreate = async () => {
    if (!createPrompt.trim() && createMode !== 'edit') return;
    setIsGenerating(true);
    setGeneratedMedia(null);

    try {
        if (createMode === 'image') {
            await checkApiKeySelection();
            const response = await ai.models.generateContent({
                model: 'gemini-3-pro-image-preview',
                contents: { parts: [{ text: createPrompt }] },
                config: {
                    imageConfig: { aspectRatio, imageSize }
                }
            });
            // Find image part
            for (const part of response.candidates?.[0]?.content?.parts || []) {
                if (part.inlineData) {
                    setGeneratedMedia(`data:${part.inlineData.mimeType};base64,${part.inlineData.data}`);
                    break;
                }
            }
        } else if (createMode === 'video') {
             await checkApiKeySelection();
             let operation = await ai.models.generateVideos({
                 model: 'veo-3.1-fast-generate-preview',
                 prompt: createPrompt,
                 config: { numberOfVideos: 1, resolution: '720p', aspectRatio: aspectRatio as any }
             });
             // Polling for video
             while (!operation.done) {
                 await new Promise(r => setTimeout(r, 5000));
                 operation = await ai.operations.getVideosOperation({operation});
             }
             const uri = operation.response?.generatedVideos?.[0]?.video?.uri;
             if (uri) {
                 // Fetch with API key appended
                 const vidRes = await fetch(`${uri}&key=${process.env.API_KEY}`);
                 const blob = await vidRes.blob();
                 setGeneratedMedia(URL.createObjectURL(blob));
             }
        } else if (createMode === 'edit') {
             if (!referenceImage) throw new Error("Reference image required for editing");
             const response = await ai.models.generateContent({
                 model: 'gemini-2.5-flash-image',
                 contents: {
                     parts: [
                         { inlineData: { data: referenceImage.data, mimeType: referenceImage.mimeType } },
                         { text: createPrompt }
                     ]
                 }
             });
             for (const part of response.candidates?.[0]?.content?.parts || []) {
                if (part.inlineData) {
                    setGeneratedMedia(`data:${part.inlineData.mimeType};base64,${part.inlineData.data}`);
                    break;
                }
            }
        }
    } catch (e: any) {
        alert("Generation failed: " + e.message);
    } finally {
        setIsGenerating(false);
    }
  };

  const handleRefImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
        const base64 = (reader.result as string).split(',')[1];
        setReferenceImage({ data: base64, mimeType: file.type });
    };
    reader.readAsDataURL(file);
  };

  // --- Live Logic ---

  const liveSessionRef = useRef<any>(null);

  const toggleLive = async () => {
    if (isLiveConnected) {
        if (liveSessionRef.current) {
            window.location.reload(); 
        }
        setIsLiveConnected(false);
        setLiveStatus("Disconnected");
    } else {
        setLiveStatus("Connecting...");
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const audioContext = new window.AudioContext({ sampleRate: 16000 });
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            // Connect to Live API
            const sessionPromise = ai.live.connect({
                model: 'gemini-2.5-flash-native-audio-preview-12-2025',
                callbacks: {
                    onopen: () => {
                        setLiveStatus("Connected - Listening");
                        setIsLiveConnected(true);
                    },
                    onmessage: async (msg: LiveServerMessage) => {
                         const audioData = msg.serverContent?.modelTurn?.parts?.[0]?.inlineData?.data;
                         if (audioData) {
                             playLiveAudio(audioData);
                         }
                    },
                    onclose: () => {
                        setLiveStatus("Disconnected");
                        setIsLiveConnected(false);
                    },
                    onerror: (e) => {
                        console.error(e);
                        setLiveStatus("Error");
                    }
                },
                config: {
                    responseModalities: [Modality.AUDIO],
                    speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Zephyr' } } }
                }
            });
            
            liveSessionRef.current = sessionPromise;

            processor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0);
                const pcmData = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    pcmData[i] = inputData[i] * 0x7FFF;
                }
                let binary = '';
                const bytes = new Uint8Array(pcmData.buffer);
                for (let i = 0; i < bytes.byteLength; i++) {
                     binary += String.fromCharCode(bytes[i]);
                }
                const b64 = btoa(binary);

                sessionPromise.then(session => {
                    session.sendRealtimeInput({
                        media: {
                            mimeType: 'audio/pcm;rate=16000',
                            data: b64
                        }
                    });
                });
                const vol = inputData.reduce((a, b) => a + Math.abs(b), 0) / inputData.length;
                setLiveVolume(vol * 5); 
            };

            source.connect(processor);
            processor.connect(audioContext.destination);

        } catch (e) {
            console.error(e);
            setLiveStatus("Connection Failed");
        }
    }
  };

  const playLiveAudio = async (base64: string) => {
      const binaryString = atob(base64);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) { bytes[i] = binaryString.charCodeAt(i); }
      
      const ctx = new (window.AudioContext || window.webkitAudioContext)({sampleRate: 24000});
      const int16 = new Int16Array(bytes.buffer);
      const float32 = new Float32Array(int16.length);
      for(let i=0; i<int16.length; i++) float32[i] = int16[i] / 32768.0;
      
      const buffer = ctx.createBuffer(1, float32.length, 24000);
      buffer.copyToChannel(float32, 0);
      
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);
      source.start();
  };

  // --- Render ---

  return (
    <div className="flex flex-col h-full bg-transparent text-white">
       {/* Header */}
       <div className="px-6 py-4 flex items-center justify-between bg-black/20 backdrop-blur-md border-b border-white/5">
           <div className="flex items-center gap-4">
            {!isSidebarOpen && (
                <button onClick={onToggleSidebar} className="text-slate-400 hover:text-white p-1 rounded hover:bg-white/5">
                    <PanelLeft size={20} />
                </button>
            )}
            <h1 className="text-lg font-bold flex items-center gap-2">
                <Sparkles size={20} className="text-yellow-400" />
                Gemini Studio
            </h1>
           </div>

           {/* Collaboration Joiner */}
           <div className="flex items-center gap-2">
             {!activeRoom ? (
               <div className="flex bg-white/5 rounded-lg border border-white/10 p-0.5">
                  <input 
                    type="text" 
                    placeholder="Room ID" 
                    value={collabRoomId}
                    onChange={(e) => setCollabRoomId(e.target.value)}
                    className="bg-transparent border-none text-xs px-2 py-1 outline-none w-20 text-white placeholder-slate-500"
                  />
                  <button 
                    onClick={() => setActiveRoom(collabRoomId)}
                    disabled={!collabRoomId}
                    className="px-2 py-1 bg-green-600/20 text-green-300 rounded text-xs hover:bg-green-600/30 disabled:opacity-50"
                  >
                    Join
                  </button>
               </div>
             ) : (
                <div className="flex items-center gap-2 bg-green-900/20 border border-green-500/20 rounded-lg px-2 py-1">
                    <span className="text-xs text-green-300 font-mono">Room: {activeRoom}</span>
                    <div className="w-px h-3 bg-green-500/20"></div>
                    <Users size={12} className="text-green-300" />
                    <span className="text-xs text-green-300">{peers.length + 1}</span>
                    <button onClick={() => { setActiveRoom(null); setIsInCall(false); endCall(); }} className="ml-1 hover:text-white text-green-400">
                        <StopCircle size={12} />
                    </button>
                </div>
             )}
           </div>
           
           <div className="flex bg-white/5 rounded-lg p-1">
               {(['chat', 'create', 'live'] as Tab[]).map(t => (
                   <button
                    key={t}
                    onClick={() => setActiveTab(t)}
                    className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === t ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
                   >
                       {t.charAt(0).toUpperCase() + t.slice(1)}
                   </button>
               ))}
           </div>
       </div>

       <div className="flex-1 overflow-hidden relative">
           
           {/* CHAT TAB */}
           {activeTab === 'chat' && (
               <div className="h-full flex flex-col relative">
                   {/* Call Grid Overlay */}
                   {isInCall && (
                     <div className="absolute top-0 left-0 right-0 h-48 bg-black/80 z-20 flex gap-2 p-2 overflow-x-auto border-b border-white/10">
                        {/* Local */}
                        <div className="relative aspect-video bg-slate-900 rounded-lg overflow-hidden border border-white/10 flex-shrink-0">
                           <video 
                              ref={el => { if(el && localStream) el.srcObject = localStream }} 
                              autoPlay muted playsInline 
                              className="w-full h-full object-cover" 
                           />
                           <span className="absolute bottom-1 left-2 text-[10px] bg-black/50 px-1 rounded text-white">You</span>
                        </div>
                        {/* Remotes */}
                        {peers.map(p => p.stream ? (
                             <div key={p.id} className="relative aspect-video bg-slate-900 rounded-lg overflow-hidden border border-white/10 flex-shrink-0">
                                <video 
                                    ref={el => { if(el && p.stream) el.srcObject = p.stream }} 
                                    autoPlay playsInline 
                                    className="w-full h-full object-cover" 
                                />
                                <span className="absolute bottom-1 left-2 text-[10px] bg-black/50 px-1 rounded text-white">{p.id.slice(0,4)}</span>
                             </div>
                        ) : null)}
                     </div>
                   )}

                   <div className={`flex-1 overflow-y-auto p-6 space-y-6 ${isInCall ? 'pt-52' : ''}`}>
                       {messages.map((m, i) => (
                           <div key={i} className={`flex gap-4 ${m.role === 'user' ? 'justify-end' : ''}`}>
                               {(m.role === 'model' || m.role === 'peer') && (
                                   <div className={`w-8 h-8 rounded-full flex items-center justify-center border ${m.role === 'peer' ? 'bg-green-500/20 border-green-500/30' : 'bg-indigo-500/20 border-indigo-500/30'}`}>
                                       {m.role === 'peer' ? <Users size={14} className="text-green-300" /> : <Sparkles size={14} className="text-indigo-300" />}
                                   </div>
                               )}
                               <div className={`max-w-[80%] p-4 rounded-2xl ${m.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-sm' : 'bg-white/5 text-slate-200 rounded-tl-sm border border-white/5'}`}>
                                   {m.role === 'peer' && <div className="text-[10px] text-green-400 mb-1 opacity-70">Peer {m.senderId?.slice(0,4)}</div>}
                                   {m.image && (
                                        <img 
                                            src={`data:${m.mimeType || 'image/jpeg'};base64,${m.image}`} 
                                            alt="uploaded" 
                                            className="mb-2 rounded-lg max-h-60" 
                                        />
                                   )}
                                   {m.video && (
                                        <video 
                                            src={`data:${m.mimeType || 'video/mp4'};base64,${m.video}`} 
                                            controls 
                                            className="mb-2 rounded-lg max-h-60" 
                                        />
                                   )}
                                   <div className="whitespace-pre-wrap">{m.text}</div>
                                   {m.role === 'model' && (
                                       <button onClick={() => handleTTS(m.text)} className="mt-2 text-slate-500 hover:text-indigo-300 transition-colors">
                                           <Volume2 size={14} />
                                       </button>
                                   )}
                               </div>
                           </div>
                       ))}
                       {isProcessing && (
                           <div className="flex gap-2 items-center text-slate-500 text-sm animate-pulse">
                               <Loader2 size={16} className="animate-spin" /> Gemini is working...
                           </div>
                       )}
                       {typingUsers.length > 0 && (
                           <div className="text-xs text-slate-500 italic ml-12">
                               {typingUsers.length} person(s) typing...
                           </div>
                       )}
                   </div>
                   
                   <div className="p-4 bg-black/20 border-t border-white/5">
                       <div className="max-w-3xl mx-auto space-y-2">
                           {/* Config Toggles */}
                           <div className="flex items-center justify-between pb-2">
                               <div className="flex gap-2 overflow-x-auto">
                                    <button onClick={() => setIsThinking(!isThinking)} className={`px-3 py-1 rounded-full text-xs border transition-colors flex items-center gap-1 ${isThinking ? 'bg-purple-500/20 border-purple-500 text-purple-300' : 'border-white/10 text-slate-400'}`}>
                                        <Wand2 size={12} /> Deep Think
                                    </button>
                                    <button onClick={() => setIsFast(!isFast)} className={`px-3 py-1 rounded-full text-xs border transition-colors flex items-center gap-1 ${isFast ? 'bg-yellow-500/20 border-yellow-500 text-yellow-300' : 'border-white/10 text-slate-400'}`}>
                                        <Loader2 size={12} /> Fast
                                    </button>
                                    <button onClick={() => setUseSearch(!useSearch)} className={`px-3 py-1 rounded-full text-xs border transition-colors flex items-center gap-1 ${useSearch ? 'bg-blue-500/20 border-blue-500 text-blue-300' : 'border-white/10 text-slate-400'}`}>
                                        <Search size={12} /> Search
                                    </button>
                               </div>

                               {activeRoom && (
                                   <button 
                                     onClick={() => {
                                         if(isInCall) {
                                             endCall();
                                             setIsInCall(false);
                                         } else {
                                             startCall();
                                             setIsInCall(true);
                                         }
                                     }}
                                     className={`p-1.5 rounded-full ${isInCall ? 'bg-red-500/20 text-red-300 border border-red-500/30' : 'bg-green-500/20 text-green-300 border border-green-500/30'}`}
                                     title={isInCall ? "End Call" : "Start Video Call"}
                                   >
                                       {isInCall ? <PhoneOff size={16} /> : <VideoIcon size={16} />}
                                   </button>
                               )}
                           </div>

                           <div className="relative">
                               <textarea
                                   value={prompt}
                                   onChange={handleTyping}
                                   className="w-full bg-white/5 border border-white/10 rounded-xl p-4 pr-24 text-white focus:ring-1 focus:ring-indigo-500 outline-none resize-none"
                                   placeholder="Ask anything..."
                                   rows={2}
                               />
                               <div className="absolute right-2 bottom-2 flex items-center gap-1">
                                   <button onClick={() => fileInputRef.current?.click()} className="p-2 text-slate-400 hover:text-white rounded hover:bg-white/10">
                                       {attachment ? <CheckCircle size={18} className="text-green-400" /> : <Upload size={18} />}
                                   </button>
                                   <button onClick={handleTranscribe} className="p-2 text-slate-400 hover:text-white rounded hover:bg-white/10">
                                       <Mic size={18} />
                                   </button>
                                   <button onClick={handleSendMessage} disabled={isProcessing} className="p-2 bg-indigo-600 text-white rounded hover:bg-indigo-500 disabled:opacity-50">
                                       <Send size={18} />
                                   </button>
                               </div>
                               <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} accept="image/*,video/*" />
                           </div>
                       </div>
                   </div>
               </div>
           )}

           {/* CREATE TAB */}
           {activeTab === 'create' && (
               <div className="h-full overflow-y-auto p-8">
                   <div className="max-w-2xl mx-auto space-y-8">
                       <div className="flex justify-center gap-4 bg-white/5 p-1 rounded-xl w-fit mx-auto">
                           {(['image', 'video', 'edit'] as CreateMode[]).map(m => (
                               <button key={m} onClick={() => setCreateMode(m)} className={`px-6 py-2 rounded-lg transition-colors ${createMode === m ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}>
                                   {m.charAt(0).toUpperCase() + m.slice(1)}
                               </button>
                           ))}
                       </div>

                       <div className="bg-black/30 border border-white/10 rounded-2xl p-6 space-y-6">
                           <div>
                               <label className="text-sm font-bold text-slate-300 uppercase block mb-2">Prompt</label>
                               <textarea 
                                   value={createPrompt} 
                                   onChange={e => setCreatePrompt(e.target.value)}
                                   className="w-full bg-black/40 border border-white/10 rounded-xl p-4 outline-none focus:border-indigo-500"
                                   rows={3}
                                   placeholder={`Describe the ${createMode} you want...`}
                               />
                           </div>

                           {createMode === 'edit' && (
                               <div>
                                   <label className="text-sm font-bold text-slate-300 uppercase block mb-2">Reference Image</label>
                                   <input type="file" onChange={handleRefImageUpload} accept="image/*" className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-500/10 file:text-indigo-400 hover:file:bg-indigo-500/20"/>
                               </div>
                           )}

                           {createMode !== 'edit' && (
                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <label className="text-sm font-bold text-slate-300 uppercase block mb-2">Aspect Ratio</label>
                                    <select value={aspectRatio} onChange={e => setAspectRatio(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-white outline-none">
                                        <option value="1:1">1:1 (Square)</option>
                                        <option value="16:9">16:9 (Landscape)</option>
                                        <option value="9:16">9:16 (Portrait)</option>
                                        <option value="4:3">4:3</option>
                                        <option value="3:4">3:4</option>
                                    </select>
                                </div>
                                {createMode === 'image' && (
                                    <div className="flex-1">
                                        <label className="text-sm font-bold text-slate-300 uppercase block mb-2">Size</label>
                                        <select value={imageSize} onChange={e => setImageSize(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-white outline-none">
                                            <option value="1K">1K</option>
                                            <option value="2K">2K</option>
                                            <option value="4K">4K</option>
                                        </select>
                                    </div>
                                )}
                            </div>
                           )}

                           <button onClick={handleCreate} disabled={isGenerating} className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl font-bold text-white shadow-lg shadow-indigo-900/40 hover:scale-[1.02] transition-transform disabled:opacity-50">
                               {isGenerating ? <div className="flex items-center justify-center gap-2"><Loader2 className="animate-spin" /> Generating...</div> : "Generate"}
                           </button>
                       </div>

                       {generatedMedia && (
                           <div className="bg-black/40 rounded-2xl overflow-hidden border border-white/10 relative group">
                               {createMode === 'video' ? (
                                   <video src={generatedMedia} controls className="w-full h-auto" autoPlay loop />
                               ) : (
                                   <img src={generatedMedia} alt="Generated" className="w-full h-auto" />
                               )}
                               <a href={generatedMedia} download={`generated_${Date.now()}.${createMode === 'video' ? 'mp4' : 'png'}`} className="absolute top-4 right-4 bg-black/60 p-2 rounded-lg text-white opacity-0 group-hover:opacity-100 transition-opacity">
                                   <Download size={20} />
                               </a>
                           </div>
                       )}
                   </div>
               </div>
           )}

           {/* LIVE TAB */}
           {activeTab === 'live' && (
               <div className="h-full flex flex-col items-center justify-center p-8 relative overflow-hidden">
                   {/* Visualizer Background */}
                   <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="w-96 h-96 bg-indigo-500/20 rounded-full blur-[100px] animate-pulse" style={{ transform: `scale(${1 + liveVolume})` }}></div>
                   </div>

                   <div className="z-10 text-center space-y-8">
                       <h2 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-200 to-purple-200">
                           {liveStatus}
                       </h2>
                       
                       <button 
                        onClick={toggleLive}
                        className={`w-24 h-24 rounded-full flex items-center justify-center shadow-2xl transition-all hover:scale-105 ${isLiveConnected ? 'bg-red-500/20 border-2 border-red-500 text-red-400' : 'bg-indigo-600 border-2 border-indigo-400 text-white'}`}
                       >
                           {isLiveConnected ? <StopCircle size={40} /> : <Mic size={40} />}
                       </button>

                       <p className="text-slate-400 max-w-md mx-auto">
                           {isLiveConnected 
                            ? "Listening... Speak naturally to Gemini." 
                            : "Start a real-time voice conversation with Gemini 2.5."}
                       </p>
                   </div>
               </div>
           )}

       </div>
    </div>
  );
}

const CheckCircle = ({size, className}: any) => <div className={className}><svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>;