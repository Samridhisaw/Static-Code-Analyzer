#include <stdio.h>
#include <string.h>


void rule_unused_function() {
    printf("This function is never used.\n");

}


void rule_constant_conditions() {
    if (1) {
        printf("Condition always true\n");
    }

    while (0) {
        printf("This will never run\n");
    }
}


void rule_empty_body() {
    if (1) {

    }  

    for (int i = 0; i < 2; i++) {

    }  

    while (1) {
    }
}

void rule_missing_break(int x) {
    switch (x) {
        case 1:
            printf("Case 1\n"); 
        case 2:
            printf("Case 2\n"); 
        default:
            printf("Default\n");
            break;
    }
}

void rule_uninitialized_var() {
    int x;
    printf("Value: %d\n", x);  
}

void rule_unused_var() {
    int temp = 5; 
}

void rule_unused_param(int a, int b) {
    printf("Used param: %d\n", b);  
}

int main() {
    int a;
    rule_constant_conditions();
    rule_empty_body();
    rule_missing_break();
    rule_uninitialized_var();
    rule_unused_var();
    rule_unused_param(10, 20);

    return 0;
}
