export const youtubePoller = {
  init(): void {
    console.log('YouTube poller initialized');
  },

  async startPolling(videoId: string): Promise<void> {
    // TODO: Implement polling logic
    console.log(`Starting polling for video: ${videoId}`);
  },

  async stopPolling(): Promise<void> {
    // TODO: Implement stop polling
    console.log('Stopping polling');
  },
};

