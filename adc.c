#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <linux/spi/spidev.h>
#include <stdint.h>
#include <termios.h>
#include <stdbool.h>

// -------------------- DEFINE -------------------- //
#define SPI_DEV "/dev/spidev0.0"
#define SPI_SPEED 500000
#define SPI_MODE SPI_MODE_0

#define COR_PESO 1010 
#define DFL_DIV_COR_PESO 1000 
#define NUM_SAMPLES_FOR_OFFSET 40 

typedef enum {
    PEDANA_SCARICA    = 0x00,
    PEDANA_CARICA     = 0x01,
    PEDANA_FUORIRANGE = 0x02,
    PEDANA_INSTABILE  = 0x03,
    PEDANA_NON_LETTA  = 0x04
} STATO_PEDANA;

// -------------- VARIABILI GLOBALI --------------- //
int spi_fd;
static struct termios oldt;
static bool reset_offset = false;

// ------------------- FUNZIONI ------------------- //

void keyboard_init(void) {
    struct termios newt;
    tcgetattr(STDIN_FILENO, &oldt);
    newt = oldt;
    newt.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &newt);
}

void keyboard_restore(void) {
    tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
}

uint16_t key_pressed(void) {
    struct timeval tv = {0, 0};
    fd_set fds;
    unsigned char c;
    FD_ZERO(&fds);
    FD_SET(STDIN_FILENO, &fds);
    if (select(STDIN_FILENO + 1, &fds, NULL, NULL, &tv) > 0) {
        if (read(STDIN_FILENO, &c, 1) == 1) return c;
    }
    return -1;
}

static int ltc2430_read(int spi_fd, int32_t *value) {
    uint8_t rx[4], tx[4] = {0, 0, 0, 0};
    struct spi_ioc_transfer tr = {
        .tx_buf = (unsigned long)tx,
        .rx_buf = (unsigned long)rx,
        .len = 4,
        .speed_hz = SPI_SPEED,
        .bits_per_word = 8,
    };

    if (ioctl(spi_fd, SPI_IOC_MESSAGE(1), &tr) < 0) return -1;
    
    uint32_t raw = ((uint32_t)rx[0] << 24) | ((uint32_t)rx[1] << 16) |
                   ((uint32_t)rx[2] << 8)  | (uint32_t)rx[3];
    
    if (raw & 0x80000000) return 1; // Dato non pronto
    
    int32_t adc = (raw >> 6) & 0x00FFFFFF;
    if (raw & 0x40000000) adc |= 0xFF000000;
    
    *value = adc;
    return 0;
}

STATO_PEDANA verificaPedana(void) {
    static int32_t offset = 0;
    static uint32_t somma40val = 0;
    static uint16_t NvalidRead = 0;
    int32_t adc = 0, adcMSB = 0, PESO_in_gr = 0;
    
    // Se Python invia il comando di tara, resettiamo i contatori
    if (reset_offset) {
        NvalidRead = 0;
        somma40val = 0;
        reset_offset = false;
        printf("RESET_START\n"); // Segnale per Python
    }

    if(ltc2430_read(spi_fd, &adc) == 0) {
        adcMSB = adc >> 8;
        if(NvalidRead < NUM_SAMPLES_FOR_OFFSET) {
            somma40val += adcMSB;
            NvalidRead++;
            if(NvalidRead == NUM_SAMPLES_FOR_OFFSET)
                offset = somma40val / NUM_SAMPLES_FOR_OFFSET;
            
            // Stampiamo un formato facilmente leggibile da Python
            printf("CALIB:%d\n", NvalidRead); 
        } else {
            PESO_in_gr = ((adcMSB - offset) * 25 * COR_PESO) / DFL_DIV_COR_PESO;
            printf("PESO:%d\n", PESO_in_gr);
        }
        return PEDANA_CARICA;
    }
    return PEDANA_NON_LETTA;
}

int main(void) {
    bool exit = false;
    int k = 0;

    printf("\n*******************************************************\n");
    printf("**** Progetto SigmaDelta - Solo Lettura ADC       ****\n");
    printf("*******************************************************\n\n");

    keyboard_init();

    spi_fd = open(SPI_DEV, O_RDWR);
    if (spi_fd < 0) {
        perror("Errore apertura SPI (Verifica che sia abilitato)");
        keyboard_restore();
        return 1;
    }

    uint8_t mode = SPI_MODE;
    ioctl(spi_fd, SPI_IOC_WR_MODE, &mode);
    ioctl(spi_fd, SPI_IOC_WR_MAX_SPEED_HZ, &(uint32_t){SPI_SPEED});

    // 1. ATTESA AVVIO
    printf("Premi un tasto per AVVIARE la lettura\n");
    while(key_pressed() == (uint16_t)-1) {
        usleep(100000); // Evita di sovraccaricare la CPU mentre aspetta
    }

    // 2. LOOP DI LETTURA
    printf("Avvio loop di lettura... Premi 't' per TARA o altri tasti per uscire.\n");
    
    exit = false; // Reset variabile per il secondo loop
    while(!exit) {
        verificaPedana();
        usleep(250000); // 4 letture al secondo

        k = key_pressed();
        if (k != (uint16_t)-1) {
            if (k == 't') {
                reset_offset = true; // Attiva la ricalibrazione nella funzione verificaPedana
            } else {
                exit = true; // Esce dal programma con qualsiasi altro tasto
            }
        }
    }

    // 3. CHIUSURA
    close(spi_fd);
    keyboard_restore();
    printf("\nFine programma.\n");
    return 0;
}
