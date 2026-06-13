/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Customer, KhataTransaction } from '../types';

export const mockCustomers: Customer[] = [
  {
    id: "cust-1",
    name: "Rajesh Kumar",
    phone: "+91 98765 43210",
    status: "Frequent",
    khataBalance: 0,
    avgBasket: 850,
    lifetimeSpend: 42500,
    lastOrderDate: "2026-06-12T18:30:00Z"
  },
  {
    id: "cust-2",
    name: "Anjali Sharma",
    phone: "+91 99887 76655",
    status: "Overdue",
    khataBalance: -4250,
    avgBasket: 1200,
    lifetimeSpend: 18900,
    lastOrderDate: "2026-06-10T14:15:00Z"
  },
  {
    id: "cust-3",
    name: "Suresh Gupta",
    phone: "+91 91234 56789",
    status: "Standard",
    khataBalance: -150,
    avgBasket: 350,
    lifetimeSpend: 4100,
    lastOrderDate: "2026-06-13T10:12:00Z"
  },
  {
    id: "cust-4",
    name: "Meera Nair",
    phone: "+91 98876 54321",
    status: "Frequent",
    khataBalance: 500, // advance payment or credit
    avgBasket: 950,
    lifetimeSpend: 23400,
    lastOrderDate: "2026-06-13T08:45:00Z"
  },
  {
    id: "cust-5",
    name: "Rohan Malhotra",
    phone: "+91 95432 10987",
    status: "Standard",
    khataBalance: -800,
    avgBasket: 600,
    lifetimeSpend: 8200,
    lastOrderDate: "2026-06-11T11:20:00Z"
  }
];

export const mockKhataTransactions: KhataTransaction[] = [
  {
    id: "txn-1",
    customerId: "cust-2",
    customerName: "Anjali Sharma",
    type: "credit",
    amount: 2200,
    date: "2026-06-08T17:00:00Z",
    description: "Purchase of Atta and Cooking Oil"
  },
  {
    id: "txn-2",
    customerId: "cust-2",
    customerName: "Anjali Sharma",
    type: "credit",
    amount: 2050,
    date: "2026-06-10T14:15:00Z",
    description: "Purchase of Dairy products and tea"
  },
  {
    id: "txn-3",
    customerId: "cust-3",
    customerName: "Suresh Gupta",
    type: "credit",
    amount: 350,
    date: "2026-06-13T10:12:00Z",
    description: "Daily snacks and paratha packet"
  },
  {
    id: "txn-4",
    customerId: "cust-1",
    customerName: "Rajesh Kumar",
    type: "payment",
    amount: 1200,
    date: "2026-06-13T04:41:44Z", // Matches "Khata payment received: 1200"
    description: "Settle outstanding balance"
  },
  {
    id: "txn-5",
    customerId: "cust-4",
    customerName: "Meera Nair",
    type: "payment",
    amount: 500,
    date: "2026-06-13T08:45:00Z",
    description: "Advance deposit for next delivery"
  }
];
