#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX 100

struct Patient {
    int id;
    char name[50];
    int age;
    char ailment[50];
};

struct Queue {
    struct Patient patients[MAX];
    int front;
    int rear;
};

struct Queue q = {.front = -1, .rear = -1};
int next_id = 1;

int main() {
    // Crucial: Disable BOTH stdout and stdin buffering to keep Python and C perfectly in sync
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    int command;
    char name[50];
    int age;
    char ailment[50];

    // Loop indefinitely waiting for instructions from the Python subprocess
    while (scanf("%d", &command) != EOF) {
        if (command == 1) { // 1. ENQUEUE
            if (scanf("%s %d %s", name, &age, ailment) != 3) {
                continue; 
            }
            if (q.rear == MAX - 1) {
                printf("ERROR_FULL\n");
            } else {
                if (q.front == -1) q.front = 0;
                q.rear++;
                q.patients[q.rear].id = next_id++;
                strncpy(q.patients[q.rear].name, name, 49);
                q.patients[q.rear].age = age;
                strncpy(q.patients[q.rear].ailment, ailment, 49);
                
                // Return status format to match Python's parsing split
                printf("SUCCESS_REG %d\n", q.patients[q.rear].id);
            }
        } 
        else if (command == 2) { // 2. DEQUEUE
            if (q.front == -1 || q.front > q.rear) {
                printf("EMPTY\n");
            } else {
                struct Patient p = q.patients[q.front];
                q.front++;
                // FIXED: Changed spaces to '|' characters so Python can unpack it!
                printf("CALLED %d|%s|%d|%s\n", p.id, p.name, p.age, p.ailment);
            }
        } 
        else if (command == 3) { // 3. MONITOR LIST
            if (q.front == -1 || q.front > q.rear) {
                printf("LIST_COUNT 0\n");
            } else {
                int count = q.rear - q.front + 1;
                printf("LIST_COUNT %d\n", count);
                for (int i = q.front; i <= q.rear; i++) {
                    // FIXED: Changed spaces to '|' characters so Python can unpack it!
                    printf("ITEM %d|%s|%d|%s\n", q.patients[i].id, q.patients[i].name, q.patients[i].age, q.patients[i].ailment);
                }
            }
        }
        else if (command == 4) { // 4. EXIT
            break;
        }
    }
    return 0;
}