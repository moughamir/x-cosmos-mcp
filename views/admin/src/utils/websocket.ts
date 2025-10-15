const socketUrl = `ws://${window.location.host}/ws/pipeline-progress`;

let socket: WebSocket | null = null;
let listeners: ((data: any) => void)[] = [];

const connect = () => {
    socket = new WebSocket(socketUrl);

    socket.onopen = () => {
        console.log("WebSocket connected");
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        listeners.forEach(listener => listener(data));
    };

    socket.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting in 5 seconds...");
        setTimeout(connect, 5000);
    };

    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        socket?.close();
    };
};

export const subscribe = (callback: (data: any) => void) => {
    if (!socket) {
        connect();
    }
    listeners.push(callback);

    return () => {
        listeners = listeners.filter(l => l !== callback);
    };
};
